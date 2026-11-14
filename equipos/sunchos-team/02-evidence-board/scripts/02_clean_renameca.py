"""Limpieza forense y estandarizacion de CONAGUA RENAMECA (D1 y D2) para Yucatan.

Hallazgos forenses verificados en datos fuente:
1. Calidad_del_Agua_Subterranea_a_2025.xlsx contiene 608 sitios nacionales y 0 sitios en Yucatan.
2. Calidad_del_Agua_Subterranea_p_2012-2025.xlsx contiene 2,875 sitios nacionales (121 en Yucatan)
   con un registro agregado por sitio para el periodo 2012-2025 (mediana para N-NO3, SDT, Conductividad,
   Fluoruros, Dureza, Alcalinidad; media geometrica para Coliformes fecales; promedio para metales).
3. El encabezado CONDUCT_mS/cm reporta valores en uS/cm (verificado por razon SDT/CE ~ 0.621).
"""
import json
import re
import numpy as np
import pandas as pd
import geopandas as gpd

from config import RAW_DIR, STAGING_DIR, CRS_WGS84, CRS_METRIC, NOM127_LIMITS, norm_text


PARAM_COLUMNS = {
    "N_NO3_mg/L": ("n_no3", "mg/L"),
    "COLI_FEC_NMP/100_mL": ("coli_fec", "NMP/100 mL"),
    "SDT_mg/L": ("sdt", "mg/L"),
    "CONDUCT_mS/cm": ("conduct", "uS/cm"),  # Header dice mS/cm pero valores estan en uS/cm
    "ALC_mg/L": ("alc", "mg/L"),
    "DUR_mg/L": ("dur", "mg/L"),
    "FLUORUROS_mg/L": ("fluoruros", "mg/L"),
    "AS_TOT_mg/L": ("as_tot", "mg/L"),
    "CD_TOT_mg/L": ("cd_tot", "mg/L"),
    "CR_TOT_mg/L": ("cr_tot", "mg/L"),
    "HG_TOT_mg/L": ("hg_tot", "mg/L"),
    "PB_TOT_mg/L": ("pb_tot", "mg/L"),
    "MN_TOT_mg/L": ("mn_tot", "mg/L"),
    "FE_TOT_mg/L": ("fe_tot", "mg/L"),
}


def parse_censored_value(val):
    """Separa valores censurados (<LD, ND) en valor LD/2, 0, LD, bandera y limite."""
    if pd.isna(val):
        return np.nan, np.nan, np.nan, False, np.nan, None
    raw = str(val).strip()
    upper = raw.upper()
    if upper in {"ND", "N/D", "SD", "AUSENTE", ""}:
        return 0.0, 0.0, 0.0, True, 0.0, raw
    m = re.match(r"^<\s*([0-9]+(?:\.[0-9]+)?)$", raw)
    if m:
        ld = float(m.group(1))
        return ld / 2.0, 0.0, ld, True, ld, raw
    num = float(raw.replace(",", ""))
    return num, num, num, False, np.nan, raw


def main() -> None:
    p_hist = RAW_DIR / "D1_D2_conagua" / "Calidad_del_Agua_Subterranea_p_2012-2025.xlsx"
    p_2025 = RAW_DIR / "D1_D2_conagua" / "Calidad_del_Agua_Subterranea_a_2025.xlsx"

    df_hist = pd.read_excel(p_hist, sheet_name="CASUB 12-2025")
    df_2025 = pd.read_excel(p_2025, sheet_name="CASUB 2025")

    audit = {
        "n_nacional_2012_2025": int(len(df_hist)),
        "n_nacional_2025": int(len(df_2025)),
        "n_yucatan_2025_por_estado": int(df_2025["ESTADO"].astype(str).str.upper().str.contains("YUC", na=False).sum()),
        "n_yucatan_2025_por_bbox": int(
            (
                pd.to_numeric(df_2025["LATITUD"], errors="coerce").between(19.5, 21.7)
                & pd.to_numeric(df_2025["LONGITUD"], errors="coerce").between(-90.6, -87.3)
            ).sum()
        ),
        "n_yucatan_2012_2025_por_estado": int(df_hist["ESTADO"].astype(str).str.upper().str.contains("YUC", na=False).sum()),
        "n_bbox_yucatan_otros_estados": int(
            (
                pd.to_numeric(df_hist["LATITUD"], errors="coerce").between(19.5, 21.7)
                & pd.to_numeric(df_hist["LONGITUD"], errors="coerce").between(-90.6, -87.3)
                & ~df_hist["ESTADO"].astype(str).str.upper().str.contains("YUC", na=False)
            ).sum()
        ),
    }

    # Filtrar registros de Yucatan (como no hay Yucatan en a_2025, todo proviene de p_2012-2025)
    yuc = df_hist[df_hist["ESTADO"].astype(str).str.upper().str.contains("YUC", na=False)].copy()

    # Normalizar identificadores y textos
    yuc["site_id"] = yuc["CLAVE SITIO"].astype(str).str.strip().str.upper()
    yuc["nombre_sitio"] = yuc["SITIO"].astype(str).str.strip()
    yuc["organismo_cuenca"] = yuc["ORGANISMO_DE_CUENCA"].astype(str).str.strip()
    yuc["estado_conagua"] = yuc["ESTADO"].astype(str).str.strip()
    yuc["municipio_conagua"] = yuc["MUNICIPIO"].astype(str).str.strip()
    yuc["acuifero"] = yuc["ACUIFERO"].astype(str).str.strip()
    yuc["tipo_sitio"] = yuc["SUBTIPO"].astype(str).str.strip().str.upper()
    yuc["periodo"] = yuc["PERIODO"].astype(str).str.strip()
    yuc["semaforo_conagua"] = yuc["SEMÁFORO"].astype(str).str.strip().str.upper()
    yuc["contaminantes_conagua"] = yuc["CONTAMINANTES"].fillna("").astype(str).str.strip()
    yuc["fuente_origen"] = "CONAGUA RENAMECA CASUB 2012-2025"

    # Validar y sanear coordenadas
    yuc["latitud"] = pd.to_numeric(yuc["LATITUD"], errors="coerce")
    yuc["longitud"] = pd.to_numeric(yuc["LONGITUD"], errors="coerce")
    # Correccion defensiva si alguna longitud en Mexico viniera positiva
    pos_lon = yuc["longitud"] > 0
    if pos_lon.any():
        yuc.loc[pos_lon, "longitud"] = -yuc.loc[pos_lon, "longitud"]

    audit["duplicados_site_id"] = int(yuc["site_id"].duplicated().sum())
    audit["duplicados_coords"] = int(yuc.duplicated(subset=["latitud", "longitud"]).sum())
    audit["coords_fuera_rango_yuc"] = int(
        (~(yuc["latitud"].between(19.5, 21.7) & yuc["longitud"].between(-90.6, -87.3))).sum()
    )

    assert audit["duplicados_site_id"] == 0, "Existen claves de sitio duplicadas"

    # Parsear parametros quimicos y microbiologicos
    censored_summary = {}
    new_cols = {}
    for raw_col, (prefix, unit) in PARAM_COLUMNS.items():
        parsed = yuc[raw_col].apply(parse_censored_value)
        new_cols[f"{prefix}_val_ld2"] = [p[0] for p in parsed]
        new_cols[f"{prefix}_val_zero"] = [p[1] for p in parsed]
        new_cols[f"{prefix}_val_ld"] = [p[2] for p in parsed]
        new_cols[f"{prefix}_is_censored"] = [p[3] for p in parsed]
        new_cols[f"{prefix}_ld_limit"] = [p[4] for p in parsed]
        new_cols[f"{prefix}_raw"] = [p[5] for p in parsed]
        s_ld2 = pd.Series(new_cols[f"{prefix}_val_ld2"])
        s_cens = pd.Series(new_cols[f"{prefix}_is_censored"])
        censored_summary[prefix] = {
            "unidad_estandar": unit,
            "n_validos": int(s_ld2.notna().sum()),
            "n_faltantes": int(s_ld2.isna().sum()),
            "n_censurados_ld": int(s_cens.sum()),
        }
    yuc = pd.concat([yuc, pd.DataFrame(new_cols, index=yuc.index)], axis=1).copy()

    # Banderas NOM-127-SSA1-2021
    yuc["rebasa_n_no3_nom127"] = yuc["n_no3_val_ld2"] > NOM127_LIMITS["N_NO3"]["limite"]
    yuc["ratio_n_no3_nom127"] = (yuc["n_no3_val_ld2"] / NOM127_LIMITS["N_NO3"]["limite"]).round(4)

    yuc["rebasa_sdt_nom127"] = yuc["sdt_val_ld2"] > NOM127_LIMITS["SDT"]["limite"]
    yuc["ratio_sdt_nom127"] = (yuc["sdt_val_ld2"] / NOM127_LIMITS["SDT"]["limite"]).round(4)

    # Coliformes fecales: <1 (censurado) cumple con criterio de ausencia / <LD; >0 no censurado rebasa NOM-127
    yuc["rebasa_coli_nom127"] = np.where(
        yuc["coli_fec_val_ld2"].isna(),
        pd.NA,
        (~yuc["coli_fec_is_censored"]) & (yuc["coli_fec_val_ld2"] > 0),
    )
    # Umbrales complementarios CONAGUA para coliformes fecales
    yuc["coli_cat_conagua"] = yuc["CALIDAD_COLI_FEC"].fillna("Sin dato").astype(str).str.strip()
    yuc["rebasa_coli_200"] = np.where(yuc["coli_fec_val_ld2"].isna(), pd.NA, yuc["coli_fec_val_ld2"] > 200.0)
    yuc["rebasa_coli_1000"] = np.where(yuc["coli_fec_val_ld2"].isna(), pd.NA, yuc["coli_fec_val_ld2"] > 1000.0)

    # Coherencia fisica SDT / Conductividad (esperado ~0.50 - 0.80 si CE esta en uS/cm)
    yuc["ratio_sdt_conduct"] = (yuc["sdt_val_ld2"] / yuc["conduct_val_ld2"]).round(4)
    yuc["qc_sdt_conduct_ok"] = yuc["ratio_sdt_conduct"].between(0.35, 0.90)

    audit["parametros"] = censored_summary
    audit["qc_sdt_conduct_anomalos"] = int((~yuc["qc_sdt_conduct_ok"]).sum())
    audit["ratio_sdt_conduct_mediana"] = float(round(yuc["ratio_sdt_conduct"].median(), 4))
    audit["rebases_n_no3_nom127"] = int(yuc["rebasa_n_no3_nom127"].sum())
    audit["rebases_sdt_nom127"] = int(yuc["rebasa_sdt_nom127"].sum())
    audit["rebases_coli_nom127_ausencia"] = int(yuc["rebasa_coli_nom127"].dropna().sum())
    audit["rebases_coli_200_recreativo"] = int(yuc["rebasa_coli_200"].dropna().sum())
    audit["rebases_coli_1000_conagua_incumpl"] = int(yuc["rebasa_coli_1000"].dropna().sum())

    # Convertir a GeoDataFrame en EPSG:32616
    gdf = gpd.GeoDataFrame(
        yuc,
        geometry=gpd.points_from_xy(yuc["longitud"], yuc["latitud"]),
        crs=CRS_WGS84,
    ).to_crs(CRS_METRIC)

    # Conservar columnas ordenadas y limpias
    keep_cols = [
        "site_id", "nombre_sitio", "tipo_sitio", "acuifero", "organismo_cuenca",
        "estado_conagua", "municipio_conagua", "periodo", "latitud", "longitud",
        "semaforo_conagua", "contaminantes_conagua", "fuente_origen",
        "CALIDAD_ALC", "CALIDAD_CONDUC", "CALIDAD_SDT_ra", "CALIDAD_SDT_salin",
        "CALIDAD_FLUO", "CALIDAD_DUR", "CALIDAD_COLI_FEC", "CALIDAD_N_NO3", "CALIDAD_AS",
        "rebasa_n_no3_nom127", "ratio_n_no3_nom127",
        "rebasa_sdt_nom127", "ratio_sdt_nom127",
        "rebasa_coli_nom127", "coli_cat_conagua", "rebasa_coli_200", "rebasa_coli_1000",
        "ratio_sdt_conduct", "qc_sdt_conduct_ok",
    ]
    for _, (prefix, _) in PARAM_COLUMNS.items():
        keep_cols.extend([
            f"{prefix}_val_ld2", f"{prefix}_val_zero", f"{prefix}_val_ld",
            f"{prefix}_is_censored", f"{prefix}_ld_limit", f"{prefix}_raw",
        ])
    keep_cols.append("geometry")

    gdf = gdf[keep_cols]
    gdf.to_file(STAGING_DIR / "renameca_yucatan_clean.gpkg", driver="GPKG")
    with open(STAGING_DIR / "renameca_audit_log.json", "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2, ensure_ascii=False)

    print(f"[02] RENAMECA Yucatan limpio: {len(gdf)} sitios guardados.")
    print(f"     Ratio SDT/CE mediana = {audit['ratio_sdt_conduct_mediana']} (confirma uS/cm)")
    print(f"     Rebases NOM-127 -> N-NO3: {audit['rebases_n_no3_nom127']}/121 | Coli(>0): {audit['rebases_coli_nom127_ausencia']}/88 | SDT: {audit['rebases_sdt_nom127']}/121")


if __name__ == "__main__":
    main()

