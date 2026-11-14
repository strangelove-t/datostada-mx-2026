"""Construye el Modelo Estrella analitico y capas GeoJSON listas para Tableau (04_analytics_bi)."""
import pandas as pd
import geopandas as gpd

from config import STAGING_DIR, CURATED_DIR, BI_DIR, CRS_WGS84, NOM127_LIMITS


def parse_bool(val) -> bool:
    """Convierte booleanos serializados en GeoPackage ('True'/'False', 1/0, bool) de forma segura."""
    if isinstance(val, bool):
        return val
    if pd.isna(val):
        return False
    s = str(val).strip().lower()
    if s in {"true", "1", "1.0", "yes", "si"}:
        return True
    if s in {"false", "0", "0.0", "no", ""}:
        return False
    raise ValueError(f"Valor booleano no reconocido: {val!r}")


def main() -> None:
    sites = gpd.read_file(CURATED_DIR / "sitios_yucatan_curated.gpkg")
    mun = gpd.read_file(CURATED_DIR / "municipios_yucatan_curated.gpkg")
    res = gpd.read_file(STAGING_DIR / "reserva_anillo_cenotes_2025.gpkg")

    # 1. DIM_MUNICIPIO (106 municipios de Yucatan)
    # Agregar conteos de sitios RENAMECA y DENUE por municipio
    sites_per_mun = (
        sites[sites["dentro_poligono_yucatan"]]
        .groupby("cve_mun")
        .agg(
            n_sitios_renameca=("site_id", "count"),
            n_sitios_rojo=("semaforo_conagua", lambda s: int((s == "ROJO").sum())),
            n_sitios_amarillo=("semaforo_conagua", lambda s: int((s == "AMARILLO").sum())),
            n_sitios_verde=("semaforo_conagua", lambda s: int((s == "VERDE").sum())),
        )
        .reset_index()
        .rename(columns={"cve_mun": "CVEGEO"})
    )
    mun_out = mun.merge(sites_per_mun, on="CVEGEO", how="left")
    for c in ["n_sitios_renameca", "n_sitios_rojo", "n_sitios_amarillo", "n_sitios_verde"]:
        mun_out[c] = mun_out[c].fillna(0).astype(int)

    dim_mun_cols = [
        "CVEGEO", "NOMGEO", "en_decreto_2013", "en_decreto_2025_porcion",
        "en_decreto_2025", "zona_anillo_mun", "decreto_88_2025_cat",
        "unidad_geo_zona", "unidad_geo_subzona", "area_km2",
        "POBTOT", "densidad_pob_km2", "TVIVPARHAB",
        "VPH_DRENAJ", "VPH_NODREN", "VPH_LETR", "VPH_AGUADV",
        "pct_drenaje_2020", "pct_sin_drenaje_2020", "pct_letrina_2020", "pct_agua_entubada_2020",
        "n_sitios_renameca", "n_sitios_rojo", "n_sitios_amarillo", "n_sitios_verde",
    ]
    dim_municipio = (
        mun_out[dim_mun_cols]
        .rename(
            columns={
                "CVEGEO": "cve_mun",
                "NOMGEO": "nom_mun",
                "POBTOT": "pob_total_2020",
                "TVIVPARHAB": "viv_habitadas_2020",
                "VPH_DRENAJ": "viv_drenaje_2020",
                "VPH_NODREN": "viv_sin_drenaje_2020",
                "VPH_LETR": "viv_letrina_2020",
                "VPH_AGUADV": "viv_agua_entubada_2020",
            }
        )
        .sort_values("cve_mun")
    )
    dim_municipio.to_csv(BI_DIR / "dim_municipio.csv", index=False, encoding="utf-8-sig")

    # 2. DIM_PARAMETRO
    dim_param = pd.DataFrame(
        [
            {
                "param_code": k,
                "nombre_parametro": v["nombre"],
                "unidad_estandar": v["unidad"],
                "limite_nom127": v["limite"],
                "criterio_nom127": v["criterio"],
                "grupo_semaforo": v["grupo_semaforo"],
            }
            for k, v in NOM127_LIMITS.items()
        ]
    )
    dim_param.to_csv(BI_DIR / "dim_parametro.csv", index=False, encoding="utf-8-sig")

    # 3. DIM_SITIO (1 fila por sitio = 121 sitios)
    dim_sitio_cols = [
        "site_id", "nombre_sitio", "tipo_sitio", "acuifero", "organismo_cuenca",
        "municipio_conagua", "cve_mun", "nom_mun", "dentro_poligono_yucatan", "dist_frontera_yuc_m",
        "latitud", "longitud", "periodo", "fuente_origen",
        "en_decreto_2013", "en_decreto_2025", "zona_anillo_mun", "decreto_88_2025_cat",
        "en_poligono_reserva", "zona_anillo_poligono", "dist_reserva_km",
        "unidad_geo_zona", "unidad_geo_subzona",
        "dist_costa_km", "banda_costa",
        "pct_urbano_2km", "pct_agropecuario_2km", "pct_natural_2km", "pct_agua_2km",
        "entorno_2km_cat", "entorno_2km_t10", "entorno_2km_t30", "entorno_2km_forzado_bin",
        "n_denue_total_2km", "n_denue_industria_2km", "n_denue_ind_alimentaria_2km",
        "n_denue_turismo_alim_2km", "n_denue_comercio_serv_2km", "n_denue_agro_acuic_2km",
        "n_loc_2km", "pob_loc_2km", "viv_nodren_loc_2km", "viv_letr_loc_2km",
        "n_loc_5km", "pob_loc_5km", "viv_loc_5km", "viv_nodren_loc_5km", "viv_letr_loc_5km",
        "pct_nodren_loc_5km",
        "semaforo_conagua", "contaminantes_conagua",
        "ratio_sdt_conduct", "qc_sdt_conduct_ok",
        "n_no3_val_ld2", "coli_fec_val_ld2", "sdt_val_ld2", "conduct_val_ld2",
        "alc_val_ld2", "dur_val_ld2", "fluoruros_val_ld2", "as_tot_val_ld2",
        "rebasa_n_no3_nom127", "rebasa_coli_nom127", "rebasa_coli_200", "rebasa_sdt_nom127",
    ]
    dim_sitio = pd.DataFrame(sites[dim_sitio_cols]).sort_values("site_id")
    dim_sitio.to_csv(BI_DIR / "dim_sitio.csv", index=False, encoding="utf-8-sig")

    # 4. FACT_CALIDAD_SITIO (formato largo tidy: 1 fila por sitio x parametro principal)
    param_map = {
        "N_NO3": ("n_no3", "rebasa_n_no3_nom127", "CALIDAD_N_NO3"),
        "COLI_FEC": ("coli_fec", "rebasa_coli_nom127", "CALIDAD_COLI_FEC"),
        "SDT": ("sdt", "rebasa_sdt_nom127", "CALIDAD_SDT_salin"),
        "CONDUCT": ("conduct", None, "CALIDAD_CONDUC"),
    }
    fact_rows = []
    for param_code, (prefix, rebasa_col, cal_col) in param_map.items():
        lim = NOM127_LIMITS[param_code]["limite"]
        for _, r in sites.iterrows():
            val_ld2 = r[f"{prefix}_val_ld2"]
            if pd.isna(val_ld2):
                continue
            if rebasa_col is not None:
                reb = parse_bool(r[rebasa_col])
            else:
                reb = bool(float(val_ld2) > lim)
            ratio = round(float(val_ld2) / lim, 4) if lim > 0 else (1.0 if reb else 0.0)
            fact_rows.append(
                {
                    "fact_id": f"{r['site_id']}__{param_code}",
                    "site_id": r["site_id"],
                    "cve_mun": r["cve_mun"],
                    "param_code": param_code,
                    "periodo": r["periodo"],
                    "valor_ld2": r[f"{prefix}_val_ld2"],
                    "valor_zero": r[f"{prefix}_val_zero"],
                    "valor_ld": r[f"{prefix}_val_ld"],
                    "valor_raw": r[f"{prefix}_raw"],
                    "is_censored": parse_bool(r[f"{prefix}_is_censored"]),
                    "ld_limit": r[f"{prefix}_ld_limit"],
                    "limite_referencia": lim,
                    "ratio_limite": ratio,
                    "rebasa_referencia": reb,
                    "calidad_conagua": r[cal_col],
                }
            )
    fact_df = pd.DataFrame(fact_rows).sort_values(["site_id", "param_code"])
    fact_df.to_csv(BI_DIR / "fact_calidad_sitio.csv", index=False, encoding="utf-8-sig")

    # 5. Capas GeoJSON simplificadas en EPSG:4326 para Tableau
    mun_geo = mun_out[dim_mun_cols + ["geometry"]].to_crs(CRS_WGS84).copy()
    mun_geo["geometry"] = mun_geo.geometry.simplify(0.0005, preserve_topology=True)
    mun_geo.to_file(BI_DIR / "municipios_yucatan.geojson", driver="GeoJSON")

    res.to_crs(CRS_WGS84).to_file(BI_DIR / "reserva_anillo_cenotes_2025.geojson", driver="GeoJSON")

    sites_geo = sites[dim_sitio_cols + ["geometry"]].to_crs(CRS_WGS84)
    sites_geo.to_file(BI_DIR / "sitios_yucatan.geojson", driver="GeoJSON")

    print(
        f"[04] Modelo Estrella exportado en {BI_DIR}:\n"
        f"     dim_sitio={len(dim_sitio)} | dim_municipio={len(dim_municipio)} | "
        f"dim_parametro={len(dim_param)} | fact_calidad_sitio={len(fact_df)}"
    )


if __name__ == "__main__":
    main()

