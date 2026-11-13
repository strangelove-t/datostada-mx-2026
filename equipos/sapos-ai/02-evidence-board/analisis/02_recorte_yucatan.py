"""Recorta RENAMECA subterráneo a Yucatán y calcula las cifras de la exploración inicial."""
import json
import sys
import unicodedata

import pandas as pd

d = sys.argv[1]


def sin_acentos(t):
    return "".join(c for c in unicodedata.normalize("NFD", str(t)) if unicodedata.category(c) != "Mn").strip().upper()


sitios = pd.read_csv(f"{d}/sitios_nacional.csv", dtype=str)
res = pd.read_csv(f"{d}/resultados_nacional.csv", dtype=str, low_memory=False)
sitios.columns = [sin_acentos(c) for c in sitios.columns]
res.columns = [c if i > 5 else sin_acentos(c) for i, c in enumerate(res.columns)]

yuc = sitios[sitios["ESTADO"].map(sin_acentos) == "YUCATAN"].copy()
yuc["MUNICIPIO_FUENTE"] = yuc["MUNICIPIO"]
yuc["MUNICIPIO"] = yuc["MUNICIPIO"].map(sin_acentos)
ry = res[res["CLAVE SITIO"].isin(yuc["CLAVE SITIO"])].copy()
ry["ANIO"] = ry["ANO"].astype(float).astype(int)
ry["FECHA"] = pd.to_datetime(ry["FECHA REALIZACION"].astype(float), unit="D", origin="1899-12-30").dt.date
yuc.to_csv(f"{d}/sitios_yucatan.csv", index=False, encoding="utf-8-sig")
ry.to_csv(f"{d}/resultados_yucatan.csv", index=False, encoding="utf-8-sig")


def medido(col):
    v = ry[col].astype("string").str.strip()
    censurado = v.str.startswith("<").fillna(False)
    x = pd.to_numeric(v.str.lstrip("<>"), errors="coerce")
    return x, censurado


def sobre(col, limite):
    x, cens = medido(col)
    ok = x.notna()
    exc = (x > limite) & ~cens
    return {
        "muestras": int(ok.sum()),
        "sobre_referencia": int(exc.sum()),
        "pct": round(exc.sum() / ok.sum() * 100, 1),
        "sitios_medidos": int(ry.loc[ok, "CLAVE SITIO"].nunique()),
        "sitios_alguna_vez": int(ry.loc[exc, "CLAVE SITIO"].nunique()),
    }


anios = ry.groupby("CLAVE SITIO")["ANIO"].nunique()
cifras = {
    "sitios": int(len(yuc)),
    "pozos": int((yuc["SUBTIPO CUERPO AGUA"] == "POZO").sum()),
    "cenotes": int((yuc["SUBTIPO CUERPO AGUA"] == "CENOTE").sum()),
    "municipios": int(yuc["MUNICIPIO"].nunique()),
    "muestreos": int(len(ry)),
    "fecha_min": str(ry["FECHA"].min()),
    "fecha_max": str(ry["FECHA"].max()),
    "sitios_8_anios_o_mas": int((anios >= 8).sum()),
    "sitios_2_anios": int((anios <= 2).sum()),
    "coliformes_fecales_detectados": sobre("COLI_FEC", 1),
    "dureza_mayor_500": sobre("DUR_TOT", 500),
    "sdt_mayor_1000": sobre("SDT", 1000),
    "cloruros_mayor_250_sin_limite_en_norma_vigente": sobre("CLORUROS_TOT", 250),
    "nitratos_N_mayor_11": sobre("N_NO3", 11),
    "plomo_mayor_0.01": sobre("PB_TOT", 0.01),
    "mercurio_mayor_0.006": sobre("HG_TOT", 0.006),
    "cadmio_mayor_0.003": sobre("CD_TOT", 0.003),
    "arsenico_mayor_0.01": sobre("AS_TOT", 0.01),
    "arsenico_mayor_0.025": sobre("AS_TOT", 0.025),
}
json.dump(cifras, open(f"{d}/cifras_exploracion_inicial.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(json.dumps(cifras, ensure_ascii=False, indent=1))
