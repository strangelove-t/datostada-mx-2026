"""Enriquecimiento geoespacial forense en EPSG:32616 (UTM Zona 16N):
1. Spatial join de sitios RENAMECA contra municipios INEGI (31mun) + auditoria de discrepancias.
2. Clasificacion triple de Anillo:
   - Criterio primario (DataBrief): 24 municipios Decreto 88/2025 (Dentro vs Fuera).
   - Criterio estricto (Poligono legal): 121 vertices externos + 8 internos Decreto 88/2025 + distancia al poligono.
   - Criterio hidrogeologico ampliado: 54 municipios Unidad Geohidrologica (Recarga / Transito / Descarga / Fuera).
3. Distancia geodesica real a la linea de costa del Golfo de Mexico (dist_costa_km).
4. Buffer de 2,000 m sobre Uso de Suelo Serie VII (excluyendo mar abierto) -> Opcion A + sensibilidad.
5. Presion puntual actual en buffer de 2,000 m: DENUE (unidades economicas por sector SCIAN) e ITER 2020 (localidades, poblacion y viviendas sin drenaje/letrina en 2 km y 5 km).
"""
import json
import re
import zipfile
import numpy as np
import pandas as pd
import geopandas as gpd

from config import RAW_DIR, STAGING_DIR, CURATED_DIR, CRS_WGS84, CRS_METRIC, norm_text


def dms_to_dd(val) -> float:
    """Convierte cadena DMS de INEGI (ej. 89°40'51.191\" W) a grados decimales."""
    if pd.isna(val):
        return np.nan
    s = str(val).strip()
    m = re.match(r"^(\d+)[°\s]+(\d+)['\s]+([0-9.]+)[\"\s]*([NSEW])$", s, re.IGNORECASE)
    if not m:
        return np.nan
    deg, mins, secs, hemi = float(m.group(1)), float(m.group(2)), float(m.group(3)), m.group(4).upper()
    dd = deg + mins / 60.0 + secs / 3600.0
    if hemi in {"S", "W"}:
        dd = -dd
    return dd


def classify_entorno_option_a(row, threshold_antropico: float = 20.0) -> str:
    """Clasifica entorno en buffer 2 km segun Opcion A (con categoria Natural y Mixto)."""
    urb = row["pct_urbano_2km"]
    agr = row["pct_agropecuario_2km"]
    antrop = urb + agr
    if antrop < threshold_antropico:
        return "Natural / Sin presion dominante"
    if urb >= 15.0 and agr >= 15.0 and (max(urb, agr) / max(min(urb, agr), 0.01)) < 1.5:
        return "Mixto (Urbano-Agricola)"
    if urb > agr:
        return "Urbano"
    return "Agricola"


def main() -> None:
    sites = gpd.read_file(STAGING_DIR / "renameca_yucatan_clean.gpkg").to_crs(CRS_METRIC)
    mun = gpd.read_file(STAGING_DIR / "municipios_yucatan.gpkg").to_crs(CRS_METRIC)
    res = gpd.read_file(STAGING_DIR / "reserva_anillo_cenotes_2025.gpkg").to_crs(CRS_METRIC)
    usv = gpd.read_file(STAGING_DIR / "usv_serieVII_yucatan.gpkg").to_crs(CRS_METRIC)
    coast = gpd.read_file(STAGING_DIR / "costa_yucatan.gpkg").to_crs(CRS_METRIC)

    res_poly = res.geometry.iloc[0]
    coast_geom = coast.geometry.iloc[0]

    # 1. Spatial join municipal y verificacion fronteriza
    mun_cols = [
        "CVEGEO", "NOMGEO", "en_decreto_2013", "en_decreto_2025_porcion",
        "en_decreto_2025", "zona_anillo_mun", "decreto_88_2025_cat",
        "unidad_geo_zona", "unidad_geo_subzona", "geometry",
    ]
    sj = gpd.sjoin(sites, mun[mun_cols], how="left", predicate="within")
    sj = sj.drop(columns=[c for c in ["index_right"] if c in sj.columns])

    sj["dentro_poligono_yucatan"] = sj["CVEGEO"].notna()
    sj["dist_frontera_yuc_m"] = 0.0

    # Para sitios que caen milimetros/metros fuera del poligono estatal (ej. frontera Chemax / Q.Roo)
    mun_union = mun.geometry.union_all()
    outside_mask = ~sj["dentro_poligono_yucatan"]
    geo_anomalies = []
    if outside_mask.any():
        for idx, row in sj[outside_mask].iterrows():
            dists = mun.geometry.distance(row.geometry)
            nearest_idx = dists.idxmin()
            dist_m = float(dists.loc[nearest_idx])
            nearest_mun = mun.loc[nearest_idx]
            sj.loc[idx, "dist_frontera_yuc_m"] = round(dist_m, 1)
            # Asignar municipio mas cercano solo como referencia espacial si esta en entorno fronterizo
            for c in [
                "CVEGEO", "NOMGEO", "en_decreto_2013", "en_decreto_2025_porcion",
                "en_decreto_2025", "zona_anillo_mun", "decreto_88_2025_cat",
                "unidad_geo_zona", "unidad_geo_subzona",
            ]:
                sj.loc[idx, c] = nearest_mun[c]
            geo_anomalies.append({
                "site_id": row["site_id"],
                "municipio_conagua": row["municipio_conagua"],
                "municipio_inegi_mas_cercano": nearest_mun["NOMGEO"],
                "dist_poligono_yucatan_m": round(dist_m, 1),
                "latitud": float(row["latitud"]),
                "longitud": float(row["longitud"]),
                "nota": "Sitio reportado como Yucatan por CONAGUA cuyas coordenadas caen fuera del poligono estatal INEGI (probable franja limitrofe con Quintana Roo).",
            })

    # Auditar discrepancias entre texto municipio CONAGUA vs spatial join INEGI
    sj["mun_conagua_norm"] = sj["municipio_conagua"].apply(norm_text)
    sj["mun_inegi_norm"] = sj["NOMGEO"].apply(norm_text)
    mismatch_df = sj[sj["mun_conagua_norm"] != sj["mun_inegi_norm"]][
        ["site_id", "municipio_conagua", "NOMGEO", "CVEGEO", "dentro_poligono_yucatan"]
    ]

    # 2. Clasificacion contra poligonal exacta de la Reserva y distancia a la costa
    sj["en_poligono_reserva"] = sj.geometry.within(res_poly)
    sj["zona_anillo_poligono"] = sj["en_poligono_reserva"].map({True: "Dentro Reserva", False: "Fuera Reserva"})
    sj["dist_reserva_km"] = (sj.geometry.distance(res_poly) / 1000.0).round(3)
    sj["dist_costa_km"] = (sj.geometry.distance(coast_geom) / 1000.0).round(3)
    sj["banda_costa"] = pd.cut(
        sj["dist_costa_km"],
        bins=[-0.01, 20.0, 50.0, 999.0],
        labels=["Costa (<20 km)", "Intermedia (20-50 km)", "Interior (>50 km)"],
    ).astype(str)

    # 3. Buffer de 2,000 m e interseccion con USV Serie VII (excluyendo mar abierto al usar solo poligonos USV)
    buffers_2km = gpd.GeoDataFrame(
        {"site_id": sj["site_id"], "geometry": sj.geometry.buffer(2000.0)},
        crs=CRS_METRIC,
    )
    usv_simple = usv[["macro_clase", "DESCRIPCIO", "geometry"]].copy()
    inter = gpd.overlay(buffers_2km, usv_simple, how="intersection", keep_geom_type=False)
    inter["area_m2"] = inter.geometry.area

    pivot_area = (
        inter.groupby(["site_id", "macro_clase"])["area_m2"]
        .sum()
        .unstack(fill_value=0.0)
        .reset_index()
    )
    for col in ["URBANO", "AGROPECUARIO", "NATURAL", "CUERPO_AGUA", "OTROS"]:
        if col not in pivot_area.columns:
            pivot_area[col] = 0.0

    # Denominador terrestre efectivo (excluye cuerpos de agua y mar abierto para no diluir sitios costeros)
    pivot_area["area_tierra_m2"] = (
        pivot_area["URBANO"] + pivot_area["AGROPECUARIO"] + pivot_area["NATURAL"] + pivot_area["OTROS"]
    )
    pivot_area["area_usv_total_m2"] = pivot_area["area_tierra_m2"] + pivot_area["CUERPO_AGUA"]
    denom = pivot_area["area_tierra_m2"].replace(0, np.nan).fillna(pivot_area["area_usv_total_m2"])

    pivot_area["pct_urbano_2km"] = (pivot_area["URBANO"] / denom * 100.0).round(2)
    pivot_area["pct_agropecuario_2km"] = (pivot_area["AGROPECUARIO"] / denom * 100.0).round(2)
    pivot_area["pct_natural_2km"] = (pivot_area["NATURAL"] / denom * 100.0).round(2)
    pivot_area["pct_agua_2km"] = (pivot_area["CUERPO_AGUA"] / pivot_area["area_usv_total_m2"] * 100.0).round(2)

    pivot_area["entorno_2km_cat"] = pivot_area.apply(lambda r: classify_entorno_option_a(r, 20.0), axis=1)
    pivot_area["entorno_2km_t10"] = pivot_area.apply(lambda r: classify_entorno_option_a(r, 10.0), axis=1)
    pivot_area["entorno_2km_t30"] = pivot_area.apply(lambda r: classify_entorno_option_a(r, 30.0), axis=1)
    pivot_area["entorno_2km_forzado_bin"] = np.where(
        pivot_area["pct_urbano_2km"] >= pivot_area["pct_agropecuario_2km"], "Urbano", "Agricola"
    )

    sj = sj.merge(
        pivot_area[
            [
                "site_id", "pct_urbano_2km", "pct_agropecuario_2km", "pct_natural_2km",
                "pct_agua_2km", "entorno_2km_cat", "entorno_2km_t10", "entorno_2km_t30",
                "entorno_2km_forzado_bin",
            ]
        ],
        on="site_id",
        how="left",
    )

    # 4. Presion puntual actual: DENUE Yucatan en buffer de 2,000 m
    z_denue = RAW_DIR / "C2_denue" / "denue_31_csv.zip"
    with zipfile.ZipFile(z_denue) as zf:
        with zf.open("conjunto_de_datos/denue_inegi_31_.csv") as f:
            dn = pd.read_csv(
                f,
                encoding="latin1",
                usecols=["id", "codigo_act", "per_ocu", "latitud", "longitud"],
            )
    dn["scian2"] = dn["codigo_act"].astype(str).str.zfill(6).str[:2]
    dn["scian3"] = dn["codigo_act"].astype(str).str.zfill(6).str[:3]
    gdf_dn = gpd.GeoDataFrame(
        dn[["id", "scian2", "scian3", "per_ocu"]],
        geometry=gpd.points_from_xy(dn["longitud"], dn["latitud"]),
        crs=CRS_WGS84,
    ).to_crs(CRS_METRIC)

    dn_in_buf = gpd.sjoin(gdf_dn, buffers_2km, how="inner", predicate="within")
    dn_agg = (
        dn_in_buf.groupby("site_id")
        .agg(
            n_denue_total_2km=("id", "count"),
            n_denue_industria_2km=("scian2", lambda s: int(s.isin(["31", "32", "33"]).sum())),
            n_denue_ind_alimentaria_2km=("scian3", lambda s: int((s == "311").sum())),
            n_denue_turismo_alim_2km=("scian2", lambda s: int((s == "72").sum())),
            n_denue_comercio_serv_2km=("scian2", lambda s: int(s.isin(["46", "81"]).sum())),
            n_denue_agro_acuic_2km=("scian2", lambda s: int((s == "11").sum())),
        )
        .reset_index()
    )
    sj = sj.merge(dn_agg, on="site_id", how="left")
    for c in [
        "n_denue_total_2km", "n_denue_industria_2km", "n_denue_ind_alimentaria_2km",
        "n_denue_turismo_alim_2km", "n_denue_comercio_serv_2km", "n_denue_agro_acuic_2km",
    ]:
        sj[c] = sj[c].fillna(0).astype(int)

    # 5. Localidades ITER 2020 dentro de buffers 2 km y 5 km (poblacion y carencia de drenaje local)
    iter_loc = pd.read_parquet(STAGING_DIR / "iter_2020_localidades.parquet")
    iter_loc["lat_dd"] = iter_loc["LATITUD"].apply(dms_to_dd)
    iter_loc["lon_dd"] = iter_loc["LONGITUD"].apply(dms_to_dd)
    iter_loc = iter_loc[iter_loc["lat_dd"].notna() & iter_loc["lon_dd"].notna()].copy()
    for c in ["POBTOT", "TVIVPARHAB", "VPH_DRENAJ", "VPH_NODREN", "VPH_LETR"]:
        iter_loc[c] = pd.to_numeric(iter_loc[c], errors="coerce").fillna(0.0)

    gdf_loc = gpd.GeoDataFrame(
        iter_loc[["MUN", "LOC", "NOM_LOC", "POBTOT", "TVIVPARHAB", "VPH_DRENAJ", "VPH_NODREN", "VPH_LETR"]],
        geometry=gpd.points_from_xy(iter_loc["lon_dd"], iter_loc["lat_dd"]),
        crs=CRS_WGS84,
    ).to_crs(CRS_METRIC)

    buffers_5km = gpd.GeoDataFrame(
        {"site_id": sj["site_id"], "geometry": sj.geometry.buffer(5000.0)},
        crs=CRS_METRIC,
    )
    for radius_tag, buf_gdf in [("2km", buffers_2km), ("5km", buffers_5km)]:
        loc_join = gpd.sjoin(gdf_loc, buf_gdf, how="inner", predicate="within")
        loc_agg = (
            loc_join.groupby("site_id")
            .agg(
                **{
                    f"n_loc_{radius_tag}": ("LOC", "count"),
                    f"pob_loc_{radius_tag}": ("POBTOT", "sum"),
                    f"viv_loc_{radius_tag}": ("TVIVPARHAB", "sum"),
                    f"viv_nodren_loc_{radius_tag}": ("VPH_NODREN", "sum"),
                    f"viv_letr_loc_{radius_tag}": ("VPH_LETR", "sum"),
                }
            )
            .reset_index()
        )
        sj = sj.merge(loc_agg, on="site_id", how="left")
        for c in [
            f"n_loc_{radius_tag}", f"pob_loc_{radius_tag}", f"viv_loc_{radius_tag}",
            f"viv_nodren_loc_{radius_tag}", f"viv_letr_loc_{radius_tag}",
        ]:
            sj[c] = sj[c].fillna(0).astype(int)

    sj["pct_nodren_loc_5km"] = np.where(
        sj["viv_loc_5km"] > 0,
        (sj["viv_nodren_loc_5km"] / sj["viv_loc_5km"] * 100.0).round(2),
        np.nan,
    )

    # Guardar capa curada y log de auditoria espacial
    sj = sj.rename(columns={"CVEGEO": "cve_mun", "NOMGEO": "nom_mun"})
    sj.to_file(CURATED_DIR / "sitios_yucatan_curated.gpkg", driver="GPKG")
    mun.to_file(CURATED_DIR / "municipios_yucatan_curated.gpkg", driver="GPKG")

    spatial_audit = {
        "n_sitios_curados": int(len(sj)),
        "n_dentro_poligono_yucatan": int(sj["dentro_poligono_yucatan"].sum()),
        "n_fuera_poligono_yucatan_frontera": int((~sj["dentro_poligono_yucatan"]).sum()),
        "anomalias_fronterizas": geo_anomalies,
        "discrepancias_municipio_texto_vs_inegi": mismatch_df.to_dict(orient="records"),
        "conteo_zona_mun_24": sj["zona_anillo_mun"].value_counts().to_dict(),
        "conteo_zona_poligono": sj["zona_anillo_poligono"].value_counts().to_dict(),
        "conteo_unidad_geo_54": sj["unidad_geo_zona"].value_counts().to_dict(),
        "conteo_entorno_2km_opcion_a": sj["entorno_2km_cat"].value_counts().to_dict(),
        "conteo_cruzado_mun24_x_entorno": pd.crosstab(sj["zona_anillo_mun"], sj["entorno_2km_cat"]).to_dict(),
        "conteo_cruzado_poligono_x_entorno": pd.crosstab(sj["zona_anillo_poligono"], sj["entorno_2km_cat"]).to_dict(),
    }
    with open(CURATED_DIR / "spatial_audit_log.json", "w", encoding="utf-8") as f:
        json.dump(spatial_audit, f, indent=2, ensure_ascii=False)

    print(f"[03] Enriquecimiento espacial completo ({len(sj)} sitios).")
    print("     Dentro vs Fuera (24 muns.):", spatial_audit["conteo_zona_mun_24"])
    print("     Dentro vs Fuera (Poligono):", spatial_audit["conteo_zona_poligono"])
    print("     Entorno 2km (Opcion A):", spatial_audit["conteo_entorno_2km_opcion_a"])
    print(f"     Discrepancias municipio texto vs INEGI: {len(mismatch_df)} | Sitios frontera externa: {len(geo_anomalies)}")


if __name__ == "__main__":
    main()

