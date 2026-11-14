"""Construye capas espaciales normalizadas en EPSG:32616 para Yucatan:
1. Poligono oficial de la Reserva Estatal Geohidrologica Anillo de Cenotes (Decreto 88/2025).
2. Capa municipal de Yucatan (106 municipios, Marco Geoestadistico INEGI) enriquecida con decretos y Censo 2020.
3. Linea de costa real del Golfo de Mexico (excluyendo fronteras terrestres con Campeche y Quintana Roo).
4. Recorte ligero de Uso del Suelo y Vegetacion Serie VII (INEGI) para Yucatan + 5 km.
"""
import re
import zipfile
import pypdf
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon

from config import (
    RAW_DIR,
    STAGING_DIR,
    CRS_METRIC,
    MUN_DECRETO_2013,
    MUN_DECRETO_2025,
    MUN_DECRETO_2025_PORCIONES,
    UNIDAD_GEO_54,
    norm_text,
    classify_usv_macro,
)


def extract_reserva_polygon() -> gpd.GeoDataFrame:
    """Extrae los 121 vertices externos y 8 internos (Yalahau) del Decreto 88/2025."""
    pdf_path = RAW_DIR / "D3_decretos" / "DO_Yucatan_2025-09-19_2.pdf"
    reader = pypdf.PdfReader(str(pdf_path))
    txt9 = reader.pages[8].extract_text()
    txt10 = reader.pages[9].extract_text()

    ext_text = (
        txt9.split("CUADRO DE CONSTRUCCIÓN DEL POLÍGONO EXTERNO DE LA RESERVA")[1]
        + "\n"
        + txt10.split("CUADRO DE CONSTRUCCIÓN DEL POLÍGONO INTERNO DE LA RESERVA")[0]
    )
    int_text = txt10.split("CUADRO DE CONSTRUCCIÓN DEL POLÍGONO INTERNO DE LA RESERVA")[1]

    ext_dict = {
        int(i): (float(x), float(y))
        for i, x, y in re.findall(r"(\d{1,3})\s+(\d{6}\.\d{2})\s+(\d{7}\.\d{2})", ext_text)
    }
    int_dict = {
        int(i): (float(x), float(y))
        for i, x, y in re.findall(r"(\d{1,2})\s+(\d{6}\.\d{2})\s+(\d{7}\.\d{2})", int_text)
    }

    assert len(ext_dict) == 121, f"Se esperaban 121 vertices externos, se encontraron {len(ext_dict)}"
    assert len(int_dict) == 8, f"Se esperaban 8 vertices internos, se encontraron {len(int_dict)}"

    ext_coords = [ext_dict[i] for i in range(1, 122)]
    int_coords = [int_dict[i] for i in range(1, 9)]
    poly = Polygon(ext_coords, [int_coords])
    assert poly.is_valid, "Poligono de la Reserva invalido topologicamente"

    gdf_res = gpd.GeoDataFrame(
        [
            {
                "nombre": "Reserva Estatal Geohidrologica del Anillo de Cenotes",
                "decreto": "Decreto 88/2025 (DO Yucatan 2025-09-19)",
                "area_km2_calc": round(poly.area / 1e6, 4),
                "area_ha_calc": round(poly.area / 1e4, 4),
                "area_ha_decreto": 213737.3801,
            }
        ],
        geometry=[poly],
        crs=CRS_METRIC,
    )
    out_path = STAGING_DIR / "reserva_anillo_cenotes_2025.gpkg"
    gdf_res.to_file(out_path, driver="GPKG")
    print(f"[01] Poligono Reserva guardado: {out_path.name} (area={poly.area/1e4:,.2f} ha)")
    return gdf_res


def build_municipios_and_iter() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, pd.DataFrame]:
    """Carga 31mun.shp, 31ent.shp y agrega variables municipales del Censo 2020 (ITER)."""
    z_mg = RAW_DIR / "D4_marco_geoestadistico" / "31_yucatan_MG_794551132173.zip"
    mun = gpd.read_file(f"zip://{z_mg}!conjunto_de_datos/31mun.shp").to_crs(CRS_METRIC)
    ent = gpd.read_file(f"zip://{z_mg}!conjunto_de_datos/31ent.shp").to_crs(CRS_METRIC)

    mun["nom_norm"] = mun["NOMGEO"].apply(norm_text)
    mun["en_decreto_2013"] = mun["nom_norm"].isin(MUN_DECRETO_2013)
    mun["en_decreto_2025_porcion"] = mun["nom_norm"].isin(MUN_DECRETO_2025_PORCIONES)
    mun["en_decreto_2025"] = mun["nom_norm"].isin(MUN_DECRETO_2025)
    mun["zona_anillo_mun"] = mun["en_decreto_2025"].map({True: "Dentro", False: "Fuera"})

    mun["decreto_88_2025_cat"] = "Fuera del Anillo"
    mun.loc[mun["en_decreto_2013"], "decreto_88_2025_cat"] = "Dentro - Nucleo (13 muns. 2013)"
    mun.loc[mun["en_decreto_2025_porcion"], "decreto_88_2025_cat"] = "Dentro - Ampliacion (11 muns. 2025)"

    mun["unidad_geo_zona"] = mun["nom_norm"].map(lambda x: UNIDAD_GEO_54.get(x, ("Fuera", "Fuera"))[0])
    mun["unidad_geo_subzona"] = mun["nom_norm"].map(lambda x: UNIDAD_GEO_54.get(x, ("Fuera", "Fuera"))[1])

    assert mun["en_decreto_2025"].sum() == 24, f"Deben empatar 24 municipios, empataron {mun['en_decreto_2025'].sum()}"

    # Cargar ITER 2020 (Yucatan)
    z_iter = RAW_DIR / "D6_inegi" / "iter_31_cpv2020_csv.zip"
    with zipfile.ZipFile(z_iter) as zf:
        with zf.open("iter_31_cpv2020/conjunto_de_datos/conjunto_de_datos_iter_31CSV20.csv") as f:
            iter_df = pd.read_csv(f, low_memory=False)

    num_cols = [
        "POBTOT", "TVIVPARHAB", "VPH_AGUADV", "VPH_AEASP", "VPH_AGUAFV",
        "VPH_EXCSA", "VPH_LETR", "VPH_DRENAJ", "VPH_NODREN", "VPH_DSADMA", "VPH_C_SERV",
    ]
    for c in num_cols:
        iter_df[c] = pd.to_numeric(iter_df[c], errors="coerce")

    iter_mun = iter_df[(iter_df["MUN"] > 0) & (iter_df["LOC"] == 0)].copy()
    iter_mun["CVEGEO"] = "31" + iter_mun["MUN"].astype(int).astype(str).str.zfill(3)
    iter_mun = iter_mun[["CVEGEO"] + num_cols].copy()
    iter_mun["pct_drenaje_2020"] = (iter_mun["VPH_DRENAJ"] / iter_mun["TVIVPARHAB"] * 100).round(2)
    iter_mun["pct_sin_drenaje_2020"] = (iter_mun["VPH_NODREN"] / iter_mun["TVIVPARHAB"] * 100).round(2)
    iter_mun["pct_letrina_2020"] = (iter_mun["VPH_LETR"] / iter_mun["TVIVPARHAB"] * 100).round(2)
    iter_mun["pct_agua_entubada_2020"] = (iter_mun["VPH_AGUADV"] / iter_mun["TVIVPARHAB"] * 100).round(2)
    iter_mun["area_km2"] = None  # se calcula desde geometria

    mun = mun.merge(iter_mun, on="CVEGEO", how="left")
    mun["area_km2"] = (mun.geometry.area / 1e6).round(3)
    mun["densidad_pob_km2"] = (mun["POBTOT"] / mun["area_km2"]).round(2)

    mun.to_file(STAGING_DIR / "municipios_yucatan.gpkg", driver="GPKG")
    ent.to_file(STAGING_DIR / "entidad_yucatan.gpkg", driver="GPKG")

    # Localidades puntuales ITER 2020 con coordenadas (excluyendo totales y localidades sin coords)
    iter_loc = iter_df[(iter_df["MUN"] > 0) & (iter_df["LOC"] > 0) & (iter_df["LOC"] < 9998)].copy()
    print(f"[01] Municipios procesados: {len(mun)} (24 en Decreto 88/2025, { (mun['unidad_geo_zona']!='Fuera').sum() } en Unidad Geo 54)")
    return mun, ent, iter_loc


def build_usv_and_coastline(ent: gpd.GeoDataFrame) -> None:
    """Recorta USV Serie VII a Yucatan + 5 km y extrae linea de costa real del Golfo."""
    z_usv = RAW_DIR / "D5_usv_serieVII" / "889463842781_s_USV_SerieVII_nacional.zip"
    usv_meta = gpd.read_file(f"zip://{z_usv}!conjunto_de_datos/cdv_usuev250sVII_cnal.shp", rows=1)

    ent_buf_usv = ent.to_crs(usv_meta.crs).buffer(5000)
    usv_yuc = gpd.read_file(
        f"zip://{z_usv}!conjunto_de_datos/cdv_usuev250sVII_cnal.shp",
        mask=ent_buf_usv,
    ).to_crs(CRS_METRIC)

    usv_yuc["macro_clase"] = usv_yuc["DESCRIPCIO"].apply(classify_usv_macro)
    usv_yuc.to_file(STAGING_DIR / "usv_serieVII_yucatan.gpkg", driver="GPKG")
    print(f"[01] USV Serie VII recortado a Yucatan+5km: {len(usv_yuc)} poligonos")
    print("     Distribucion macro-clases:", usv_yuc["macro_clase"].value_counts().to_dict())

    # Linea de costa real: frontera de Yucatan que NO colinda con tierra continental (Campeche / QRoo)
    # Tierra continental fuera de Yucatan = poligonos terrestres de USV (no CUERPO_AGUA) fuera de ent
    ent_union = ent.geometry.union_all()
    usv_land = usv_yuc[usv_yuc["macro_clase"] != "CUERPO_AGUA"].geometry.union_all()
    land_outside_yuc = usv_land.difference(ent_union).buffer(150)
    coastline = ent_union.boundary.difference(land_outside_yuc)

    gdf_coast = gpd.GeoDataFrame(
        [{"nombre": "Linea de costa de Yucatan (Golfo de Mexico)"}],
        geometry=[coastline],
        crs=CRS_METRIC,
    )
    gdf_coast.to_file(STAGING_DIR / "costa_yucatan.gpkg", driver="GPKG")
    print(f"[01] Linea de costa extraida: longitud = {coastline.length/1000:,.1f} km")


def main() -> None:
    extract_reserva_polygon()
    _, ent, iter_loc = build_municipios_and_iter()
    iter_loc.to_parquet(STAGING_DIR / "iter_2020_localidades.parquet", index=False)
    build_usv_and_coastline(ent)


if __name__ == "__main__":
    main()

