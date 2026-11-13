"""Evidence Board: cifras, tabla por sitio y figuras.

Uso: python 03_evidence_board.py <datos-procesados> <geojson de la península> <carpeta de salida>
"""
import json
import math
import sys

import numpy as np
import pandas as pd
from scipy.stats import kendalltau

datos, geo, salida = sys.argv[1], sys.argv[2], sys.argv[3]

TINTA, SUAVE, LINEA = "#14242b", "#4a5b63", "#c9d3d6"
FUENTE = "Segoe UI, Arial, sans-serif"
RAMPA_SAL = ["#c6dde1", "#4f9aa6", "#0a4a55"]
RAMPA_BAC = ["#f0d6c2", "#cf8552", "#8a3a12"]
CLASES = ["Nunca", "A veces", "En la mitad o más de sus muestreos"]

# Referencias: NOM-127-SSA1-2021 (tablas 2, 4, 5 y 6)
REF = {"COLI_FEC": 0, "SDT": 1000, "DUR_TOT": 500, "N_NO3": 11, "AS_TOT": 0.01,
       "CR_TOT": 0.05, "PB_TOT": 0.01, "HG_TOT": 0.006, "CD_TOT": 0.003}
ZONAS = ["Poniente", "Franja de Mérida", "Centro", "Oriente"]
CORTES = [-91, -89.9, -89.3, -88.6, -87]

sitios = pd.read_csv(f"{datos}/sitios_yucatan.csv", dtype=str)
res = pd.read_csv(f"{datos}/resultados_yucatan.csv", dtype=str, low_memory=False)
res["ANIO"] = res["ANIO"].astype(int)
sitios["lat"] = sitios["LATITUD"].astype(float)
sitios["lon"] = sitios["LONGITUD"].astype(float)
sitios["zona"] = pd.cut(sitios["lon"], CORTES, labels=ZONAS).astype(str)
sitios["subtipo"] = sitios["SUBTIPO CUERPO AGUA"].str.title()

for col, lim in REF.items():
    v = res[col].astype("string").str.strip()
    censurado = v.str.startswith("<").fillna(False)
    x = pd.to_numeric(v.str.lstrip("<>"), errors="coerce")
    res[col + "_x"] = x
    res[col + "_e"] = np.where(x.isna(), np.nan, ((x > lim) & ~censurado).astype(float))

g = res.groupby("CLAVE SITIO")
s = sitios.set_index("CLAVE SITIO")
s["muestreos"] = g.size()
s["anios"] = g["ANIO"].nunique()
for col in ("COLI_FEC", "SDT", "DUR_TOT"):
    s[col + "_n"] = g[col + "_e"].count()
    s[col + "_exc"] = g[col + "_e"].sum()
    s[col + "_pct"] = (s[col + "_exc"] / s[col + "_n"] * 100).round(1)
    s[col + "_clase"] = np.select([s[col + "_n"] == 0, s[col + "_exc"] == 0, s[col + "_pct"] < 50], [-1, 0, 1], 2)
s["SDT_mediana"] = g["SDT_x"].median().round(1)
s["DUR_mediana"] = g["DUR_TOT_x"].median().round(1)

sal = (s["SDT_clase"] == 2) | (s["DUR_TOT_clase"] == 2)
bac = s["COLI_FEC_clase"] == 2
s["atender"] = np.select([sal & bac, sal, bac], ["Ambos", "Sales o dureza", "Bacterias"], "Ninguno recurrente")

resumen = s[["NOMBRE DEL SITIO", "MUNICIPIO", "subtipo", "zona", "lat", "lon", "muestreos", "anios",
             "SDT_n", "SDT_exc", "SDT_pct", "SDT_clase", "SDT_mediana", "DUR_TOT_n", "DUR_TOT_exc", "DUR_TOT_pct",
             "DUR_TOT_clase", "DUR_mediana", "COLI_FEC_n", "COLI_FEC_exc", "COLI_FEC_pct", "COLI_FEC_clase", "atender"]]
resumen.to_csv(f"{datos}/sitios_resumen.csv", encoding="utf-8-sig")

r = res.merge(s[["zona", "subtipo", "anios"]], left_on="CLAVE SITIO", right_index=True)


def parte(df, col):
    e = df[col + "_e"].dropna()
    return {"muestreos": int(len(e)), "sobre": int(e.sum()), "pct": round(float(e.mean() * 100), 1) if len(e) else None}


cifras = {"general": {c: parte(r, c) for c in REF}}
cifras["por_zona"] = {}
for z in ZONAS:
    sz, rz = s[s["zona"] == z], r[r["zona"] == z]
    cifras["por_zona"][z] = {
        "sitios": int(len(sz)),
        "SDT": parte(rz, "SDT"), "DUR_TOT": parte(rz, "DUR_TOT"), "COLI_FEC": parte(rz, "COLI_FEC"),
        "SDT_sitios_alguna_vez": int((sz["SDT_exc"] > 0).sum()),
        "SDT_sitios_mayoria": int((sz["SDT_clase"] == 2).sum()),
        "SDT_mediana_de_sitios": round(float(sz["SDT_mediana"].median()), 1),
        "COLI_sitios_medidos": int((sz["COLI_FEC_n"] > 0).sum()),
        "COLI_sitios_detectado": int((sz["COLI_FEC_exc"] > 0).sum()),
        "COLI_FEC_solo_pozos": parte(rz[rz["subtipo"] == "Pozo"], "COLI_FEC"),
        "COLI_FEC_solo_cenotes": parte(rz[rz["subtipo"] == "Cenote"], "COLI_FEC"),
    }
cifras["por_subtipo"] = {}
for t in ("Pozo", "Cenote"):
    st, rt = s[s["subtipo"] == t], r[r["subtipo"] == t]
    cifras["por_subtipo"][t] = {
        "sitios": int(len(st)), "COLI_FEC": parte(rt, "COLI_FEC"), "SDT": parte(rt, "SDT"),
        "COLI_sitios_medidos": int((st["COLI_FEC_n"] > 0).sum()),
        "COLI_sitios_detectado": int((st["COLI_FEC_exc"] > 0).sum()),
        "COLI_sitios_mayoria": int((st["COLI_FEC_clase"] == 2).sum()),
    }
cifras["clases_por_sitio"] = {
    c: {"sin_medir": int((s[c + "_clase"] == -1).sum()), "nunca": int((s[c + "_clase"] == 0).sum()),
        "a_veces": int((s[c + "_clase"] == 1).sum()), "mayoria": int((s[c + "_clase"] == 2).sum())}
    for c in ("SDT", "DUR_TOT", "COLI_FEC")
}

# Tendencia de SDT en sitios con ocho o más años: Mann-Kendall sobre la mediana anual
largos = r[r["anios"] >= 8]
tend = []
for clave, t in largos.groupby("CLAVE SITIO"):
    a = t.groupby("ANIO")["SDT_x"].median().dropna()
    tau, p = kendalltau(a.index, a.values)
    tend.append({"sitio": clave, "anios": int(len(a)), "tau": round(float(tau), 3), "p": round(float(p), 4)})
T = pd.DataFrame(tend)
T.to_csv(f"{datos}/tendencia_sdt_sitios_largos.csv", index=False, encoding="utf-8-sig")
cifras["tendencia_sdt"] = {
    "sitios": int(len(T)), "anios_min": int(T["anios"].min()),
    "sube": int(((T.p < 0.05) & (T.tau > 0)).sum()), "baja": int(((T.p < 0.05) & (T.tau < 0)).sum()),
    "sin_tendencia": int((T.p >= 0.05).sum()),
}
col_largos = largos[largos["ANIO"] <= 2020].groupby("ANIO")["COLI_FEC_e"].agg(["mean", "count"])
cifras["coliformes_sitios_largos_2012_2020"] = {
    "min_pct": round(float(col_largos["mean"].min() * 100), 1), "max_pct": round(float(col_largos["mean"].max() * 100), 1),
    "por_anio": {int(a): [round(float(f["mean"] * 100), 1), int(f["count"])] for a, f in col_largos.iterrows()},
}
cifras["sdt_mitad_o_mas"] = {
    "sitios": int((s["SDT_clase"] == 2).sum()),
    "al_oeste_de_89.6": int(((s["SDT_clase"] == 2) & (s["lon"] < -89.6)).sum()),
}
cifras["sitios_largos"] = {"total": int((s["anios"] >= 8).sum()), "cenotes": int(((s["anios"] >= 8) & (s["subtipo"] == "Cenote")).sum())}
primer_anio = res.groupby("CLAVE SITIO")["ANIO"].min()
cifras["coliformes_cobertura"] = {
    "sin_medir_son_los_nuevos_de_2022": bool(set(s.index[s["COLI_FEC_n"] == 0]) == set(primer_anio.index[primer_anio == 2022])),
    "2022": [int(res.loc[res["ANIO"] == 2022, "COLI_FEC"].notna().sum()), int((res["ANIO"] == 2022).sum())],
    "2023": [int(res.loc[res["ANIO"] == 2023, "COLI_FEC"].notna().sum()), int((res["ANIO"] == 2023).sum())],
}
ATENDER = ["Ninguno recurrente", "Sales o dureza", "Bacterias", "Ambos"]
cifras["atender"] = {
    "por_zona": {z: {c: int(((s["zona"] == z) & (s["atender"] == c)).sum()) for c in ATENDER} for z in ZONAS},
    "total": {c: int((s["atender"] == c).sum()) for c in ATENDER},
    "sin_coliformes": {c: int(((s["atender"] == c) & (s["COLI_FEC_clase"] == -1)).sum()) for c in ATENDER},
    "ambos": sorted(f"{f['MUNICIPIO'].title()} ({f['subtipo'].lower()})" for _, f in s[s["atender"] == "Ambos"].iterrows()),
    "municipios_poniente": sorted(s.loc[s["zona"] == "Poniente", "MUNICIPIO"].str.title().unique()),
}
# Resumen por sitio con las reglas publicadas por CONAGUA (mediana; media geométrica en coliformes)
# frente al detalle por muestreo. Los valores con "<" se toman en su límite de detección.
gs = res.groupby("CLAVE SITIO")
v_col = res["COLI_FEC"].astype("string").str.strip()
res["COLI_valor"] = pd.to_numeric(v_col.str.lstrip("<>"), errors="coerce")
res["COLI_mil"] = np.where(res["COLI_valor"].isna(), np.nan, ((res["COLI_valor"] > 1000) & ~v_col.str.startswith("<").fillna(False)).astype(float))
media_geo = res.dropna(subset=["COLI_valor"]).groupby("CLAVE SITIO")["COLI_valor"].apply(lambda x: float(np.exp(np.log(x.clip(lower=1)).mean())))
alguna_mil = res.groupby("CLAVE SITIO")["COLI_mil"].sum()
mediana_no3 = gs["N_NO3_x"].median()
alguna_no3 = gs["N_NO3_e"].sum()
cifras["resumen_por_sitio"] = {
    "coliformes_sitios_medidos": int(len(media_geo)),
    "coliformes_media_geometrica_sobre_1000": int((media_geo > 1000).sum()),
    "coliformes_algun_muestreo_sobre_1000": int((alguna_mil > 0).sum()),
    "nitratos_mediana_sobre_11": int((mediana_no3 > 11).sum()),
    "nitratos_algun_muestreo_sobre_11": int((alguna_no3 > 0).sum()),
}
cifras["calidad"] = {
    "grafias_municipio_en_fuente": int(s["MUNICIPIO_FUENTE"].nunique()),
    "municipios": int(s["MUNICIPIO"].nunique()),
    "censurados_pct": {c: round(float(res[c].astype("string").str.strip().str.startswith("<").sum() / res[c].notna().sum() * 100), 1)
                       for c in ("COLI_FEC", "AS_TOT", "CR_TOT", "PB_TOT", "HG_TOT", "CD_TOT", "N_NO3", "SDT", "DUR_TOT")},
    "sitios_sin_coliformes": int((s["COLI_FEC_n"] == 0).sum()),
    "duplicados_sitio_fecha": int(res.duplicated(["CLAVE SITIO", "FECHA"]).sum()),
}
json.dump(cifras, open(f"{datos}/cifras_evidence_board.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

# ---------------- Mapas ----------------
LON0, LON1, LAT0, LAT1 = -90.55, -87.35, 19.50, 21.70
W = 520
K = math.cos(math.radians((LAT0 + LAT1) / 2))
H = round(W * (LAT1 - LAT0) / ((LON1 - LON0) * K))


def xy(lon, lat):
    return (lon - LON0) / (LON1 - LON0) * W, (LAT1 - lat) / (LAT1 - LAT0) * H


def trazo(geom):
    polis = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return "".join("M" + "L".join(f"{xy(a, b)[0]:.1f},{xy(a, b)[1]:.1f}" for a, b in anillo) + "Z" for poli in polis for anillo in poli)


estados = {f["properties"]["name"]: trazo(f["geometry"]) for f in json.load(open(geo, encoding="utf-8"))["features"]}


def mapa(col, rampa, archivo):
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="{FUENTE}">',
         f'<defs><clipPath id="c"><rect width="{W}" height="{H}"/></clipPath></defs><g clip-path="url(#c)">',
         f'<rect width="{W}" height="{H}" fill="#eef3f4"/>']
    for n in ("Campeche", "Quintana Roo"):
        o.append(f'<path d="{estados[n]}" fill="#f7f9f9" stroke="{LINEA}" stroke-width="0.8"/>')
    o.append(f'<path d="{estados["Yucatán"]}" fill="#fff" stroke="{SUAVE}" stroke-width="1.1"/>')
    for corte in CORTES[1:-1]:
        x = xy(corte, 0)[0]
        o.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="22" y2="{H}" stroke="{SUAVE}" stroke-width="0.9" stroke-dasharray="3 4"/>')
    bordes = [LON0] + CORTES[1:-1] + [LON1]
    for i, z in enumerate(ZONAS):
        x = (xy(bordes[i], 0)[0] + xy(bordes[i + 1], 0)[0]) / 2
        ancho_z = len(z) * 7.4 + 8
        o.append(f'<rect x="{x - ancho_z / 2:.1f}" y="4" width="{ancho_z:.1f}" height="15" fill="#eef3f4"/>')
        o.append(f'<text x="{x:.0f}" y="15" font-size="10" fill="{SUAVE}" letter-spacing="0.8" text-anchor="middle" font-weight="600">{z.upper()}</text>')
    radio = {-1: 2.8, 0: 3.2, 1: 4.6, 2: 6.0}
    for clase in (-1, 0, 1, 2):
        for _, f in s[s[col + "_clase"] == clase].iterrows():
            x, y = xy(f["lon"], f["lat"])
            rr = radio[clase]
            relleno = "#fff" if clase == -1 else rampa[clase]
            borde = f'stroke="{SUAVE}" stroke-width="1"' if clase == -1 else 'stroke="#fff" stroke-width="1.1"'
            if f["subtipo"] == "Cenote":
                o.append(f'<rect x="{x - rr:.1f}" y="{y - rr:.1f}" width="{2 * rr:.1f}" height="{2 * rr:.1f}" transform="rotate(45 {x:.1f} {y:.1f})" fill="{relleno}" {borde}/>')
            else:
                o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr}" fill="{relleno}" {borde}/>')
    for nombre, lat, lon, dx, dy, ancla in [("Mérida", 20.97, -89.62, -9, 16, "end"), ("Valladolid", 20.69, -88.20, 0, 22, "middle"),
                                            ("Tizimín", 21.14, -88.15, 9, -7, "start"), ("Tekax", 20.20, -89.29, 9, 13, "start"),
                                            ("Celestún", 20.86, -90.40, 4, 19, "start")]:
        x, y = xy(lon, lat)
        ancho = len(nombre) * 6.6 + 6
        x0 = {"start": x + dx - 3, "middle": x + dx - ancho / 2, "end": x + dx - ancho + 3}[ancla]
        o.append(f'<rect x="{x0:.1f}" y="{y + dy - 11:.1f}" width="{ancho:.1f}" height="14" rx="2" fill="#fff" fill-opacity="0.82"/>')
        o.append(f'<text x="{x + dx:.0f}" y="{y + dy:.0f}" font-size="11.5" font-weight="600" fill="{TINTA}" text-anchor="{ancla}">{nombre}</text>')
    o.append("</g></svg>")
    open(f"{salida}/{archivo}", "w", encoding="utf-8").write("".join(o))


mapa("SDT", RAMPA_SAL, "fig-mapa-sales.svg")
mapa("COLI_FEC", RAMPA_BAC, "fig-mapa-bacterias.svg")

# ---------------- Barras por zona ----------------


def barras(filas, color, archivo, ancho=212, etiqueta=102):
    alto_f, sup = 23, 4
    alto = sup + alto_f * len(filas) + 2
    escala = (ancho - etiqueta - 46) / 100
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}" font-family="{FUENTE}">']
    for i, (nombre, pct, n) in enumerate(filas):
        y = sup + i * alto_f
        o.append(f'<text x="0" y="{y + 12}" font-size="10.5" fill="{TINTA}">{nombre}</text>')
        o.append(f'<text x="0" y="{y + 21}" font-size="7.6" fill="{SUAVE}">{n} muestreos</text>')
        o.append(f'<rect x="{etiqueta}" y="{y + 3}" width="{100 * escala:.1f}" height="13" fill="#e7edee"/>')
        w = max(pct * escala, 1.2)
        o.append(f'<path d="M{etiqueta},{y + 3}H{etiqueta + w - 2:.1f}q2,0 2,2v9q0,2 -2,2H{etiqueta}Z" fill="{color}"/>')
        o.append(f'<text x="{etiqueta + 100 * escala + 5:.1f}" y="{y + 14}" font-size="10.5" font-weight="600" fill="{TINTA}">{pct:.1f} %</text>')
    o.append("</svg>")
    open(f"{salida}/{archivo}", "w", encoding="utf-8").write("".join(o))


for col, color, archivo in [("SDT", RAMPA_SAL[2], "fig-zona-sales.svg"), ("DUR_TOT", RAMPA_SAL[1], "fig-zona-dureza.svg"),
                            ("COLI_FEC", RAMPA_BAC[2], "fig-zona-bacterias.svg")]:
    barras([(z, cifras["por_zona"][z][col]["pct"], cifras["por_zona"][z][col]["muestreos"]) for z in ZONAS], color, archivo)
barras([(f"{t}s", cifras["por_subtipo"][t]["COLI_FEC"]["pct"], cifras["por_subtipo"][t]["COLI_FEC"]["muestreos"]) for t in ("Cenote", "Pozo")],
       RAMPA_BAC[2], "fig-subtipo-bacterias.svg")
NOMBRES = {"COLI_FEC": "Coliformes fecales", "DUR_TOT": "Dureza total", "SDT": "Sólidos disueltos", "AS_TOT": "Arsénico",
           "N_NO3": "N de nitratos", "CR_TOT": "Cromo", "PB_TOT": "Plomo", "HG_TOT": "Mercurio", "CD_TOT": "Cadmio"}
orden = sorted(REF, key=lambda c: -cifras["general"][c]["pct"])
barras([(NOMBRES[c], cifras["general"][c]["pct"], cifras["general"][c]["muestreos"]) for c in orden], SUAVE, "fig-parametros.svg")

print(json.dumps(cifras["resumen_por_sitio"], ensure_ascii=False))
print({z: (cifras["por_zona"][z]["COLI_FEC_solo_pozos"], cifras["por_zona"][z]["COLI_FEC_solo_cenotes"]) for z in ZONAS})
