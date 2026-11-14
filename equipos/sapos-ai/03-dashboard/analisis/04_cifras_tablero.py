"""Cifras del tablero: perfil de poniente a oriente, estabilidad en el tiempo y lista por municipio.

Uso: python 04_cifras_tablero.py <datos-procesados>
Escribe sitio_anio.csv y cifras_tablero.json en la misma carpeta.
"""
import json
import sys

import numpy as np
import pandas as pd

datos = sys.argv[1]
REF = {"COLI_FEC": 0, "SDT": 1000, "DUR_TOT": 500}
# La fuente asigna a Mérida un pozo del sistema de agua potable de Peto; su nombre y sus coordenadas
# (20.125, -88.922, la cabecera de Peto) lo ubican en Peto. Solo afecta a la lista por municipio.
CORRECCION_MUNICIPIO = {"OCPYU5381": "PETO"}

s = pd.read_csv(f"{datos}/sitios_resumen.csv")
res = pd.read_csv(f"{datos}/resultados_yucatan.csv", dtype=str, low_memory=False)
res["ANIO"] = res["ANIO"].astype(int)
s["MUNICIPIO"] = s["CLAVE SITIO"].map(CORRECCION_MUNICIPIO).fillna(s["MUNICIPIO"])
for col, lim in REF.items():
    v = res[col].astype("string").str.strip()
    censurado = v.str.startswith("<").fillna(False)
    x = pd.to_numeric(v.str.lstrip("<>"), errors="coerce")
    res[col + "_x"] = x
    res[col + "_e"] = np.where(x.isna(), np.nan, ((x > lim) & ~censurado).astype(float))


def spearman(a, b):
    ok = a.notna() & b.notna()
    return round(float(a[ok].rank().corr(b[ok].rank())), 2), int(ok.sum())


# 1. Estado de cada sitio en cada año: 1 si algún muestreo del año pasa la referencia, 0 si ninguno, vacío si no se midió
g = res.groupby(["CLAVE SITIO", "ANIO"])
sa = pd.DataFrame({"n": g.size(), "sal": g["SDT_e"].max(), "bac": g["COLI_FEC_e"].max()}).reset_index()
sa.to_csv(f"{datos}/sitio_anio.csv", index=False, encoding="utf-8-sig")


def estabilidad(col, tabla=None):
    tabla = sa if tabla is None else tabla
    medidos = tabla.dropna(subset=[col])
    por_sitio = medidos.groupby("CLAVE SITIO")[col].agg(["min", "max", "count"])
    largos = por_sitio[por_sitio["count"] >= 8]
    pares = iguales = 0
    for _, t in medidos.groupby("CLAVE SITIO"):
        x = t.sort_values("ANIO")[col].tolist()
        pares += len(x) - 1
        iguales += sum(a == b for a, b in zip(x, x[1:]))
    return {
        "largos": int(len(largos)), "largos_mantienen": int((largos["min"] == largos["max"]).sum()),
        "pares_de_anios": pares, "pares_iguales": iguales, "pares_iguales_pct": round(iguales / pares * 100, 1),
        "sitios": int(len(por_sitio)),
        "siempre": int(((por_sitio["min"] == 1) & (por_sitio["max"] == 1)).sum()),
        "nunca": int(((por_sitio["min"] == 0) & (por_sitio["max"] == 0)).sum()),
        "cambian": int((por_sitio["min"] != por_sitio["max"]).sum()),
        "con_un_solo_anio": int((por_sitio["count"] == 1).sum()),
    }


cifras = {"estabilidad": {"sales": estabilidad("sal"), "bacterias": estabilidad("bac")}}
v_col = res["COLI_FEC"].astype("string").str.strip()
res["COLI_30"] = np.where(res["COLI_FEC_x"].isna(), np.nan, ((res["COLI_FEC_x"] >= 30) & ~v_col.str.startswith("<").fillna(False)).astype(float))
sa30 = res.groupby(["CLAVE SITIO", "ANIO"])["COLI_30"].max().rename("bac").reset_index()
cifras["estabilidad"]["bacterias_umbral_30"] = estabilidad("bac", sa30)
for e in cifras["estabilidad"].values():
    e["mantienen"] = e["siempre"] + e["nunca"]
por_anio = res.groupby(["CLAVE SITIO", "ANIO"]).size()
fechas = pd.to_datetime(res["FECHA"])
cifras["calidad"] = {
    "sitio_anios": int(len(por_anio)), "sitio_anios_con_un_muestreo": int((por_anio == 1).sum()),
    "sitios_con_dos_muestreos": int((s["muestreos"] == 2).sum()),
    "ultima_fecha_con_coliformes": str(fechas[res["COLI_FEC_x"].notna()].max().date()),
    "limites_de_deteccion_coliformes": sorted(set(v_col[v_col.str.startswith("<").fillna(False)]), key=lambda t: float(t[1:])),
    "sin_coliformes_por_clase": {c: int(((s["COLI_FEC_n"] == 0) & (s["atender"] == c)).sum()) for c in sorted(s["atender"].unique())},
}
sub = res.merge(s[["CLAVE SITIO", "subtipo"]], on="CLAVE SITIO")
cifras["coliformes_por_subtipo"] = {t: {"muestreos": int(g["COLI_FEC_e"].count()), "con_deteccion": int(g["COLI_FEC_e"].sum()),
                                        "pct": round(float(g["COLI_FEC_e"].mean() * 100), 1)} for t, g in sub.groupby("subtipo")}

# 2. Perfil de poniente a oriente: correlación de rangos entre la posición y el porcentaje de muestreos sobre la referencia
con_bac = s[s["COLI_FEC_n"] > 0]
pozos = con_bac[con_bac["subtipo"] == "Pozo"]
cifras["perfil"] = {
    "sales_longitud": dict(zip(("rho", "sitios"), spearman(s["lon"], s["SDT_pct"]))),
    "sales_latitud": dict(zip(("rho", "sitios"), spearman(s["lat"], s["SDT_pct"]))),
    "bacterias_longitud": dict(zip(("rho", "sitios"), spearman(con_bac["lon"], con_bac["COLI_FEC_pct"]))),
    "bacterias_latitud": dict(zip(("rho", "sitios"), spearman(con_bac["lat"], con_bac["COLI_FEC_pct"]))),
    "bacterias_longitud_solo_pozos": dict(zip(("rho", "sitios"), spearman(pozos["lon"], pozos["COLI_FEC_pct"]))),
}

# 3. El patrón de sales no depende de dónde se corte: muestreos sobre la referencia al poniente y al oriente de cada meridiano
r = res.merge(s[["CLAVE SITIO", "lon"]], on="CLAVE SITIO")
cortes = []
for m in np.arange(-90.0, -88.95, 0.1):
    p, o = r[r["lon"] <= m]["SDT_e"].dropna(), r[r["lon"] > m]["SDT_e"].dropna()
    cortes.append({"meridiano": round(float(m), 1), "poniente_pct": round(float(p.mean() * 100), 1), "poniente_muestreos": int(len(p)),
                   "oriente_pct": round(float(o.mean() * 100), 1), "oriente_muestreos": int(len(o))})
cifras["sensibilidad_cortes"] = cortes

# 4. Dónde atender primero: sitios con algo recurrente por municipio
t = pd.crosstab(s["MUNICIPIO"], s["atender"])
t["sitios"] = t.sum(axis=1)
t["atender"] = t["sitios"] - t.get("Ninguno recurrente", 0)
t = t.sort_values(["atender", "sitios", "Sales o dureza"], ascending=False)
cifras["municipios"] = {
    "monitoreados": int(len(t)), "con_algo_que_atender": int((t["atender"] > 0).sum()),
    "lista": [{"municipio": m, "atender": int(f["atender"]), "sitios": int(f["sitios"])} for m, f in t.head(12).iterrows()],
}
cifras["sitios"] = {"total": int(len(s)), "muestreos_min": int(s["muestreos"].min()), "muestreos_max": int(s["muestreos"].max()),
                    "sin_medicion_de_coliformes": int((s["COLI_FEC_n"] == 0).sum())}

with open(f"{datos}/cifras_tablero.json", "w", encoding="utf-8") as f:
    json.dump(cifras, f, ensure_ascii=False, indent=1)
print(json.dumps({k: cifras[k] for k in ("estabilidad", "calidad", "coliformes_por_subtipo")}, ensure_ascii=False))
print(cortes[0], cortes[-1])
print(cifras["municipios"]["monitoreados"], cifras["municipios"]["con_algo_que_atender"], cifras["municipios"]["lista"][:6])
