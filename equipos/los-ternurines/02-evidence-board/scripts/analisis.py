"""Evidence Board - El agua que no vemos (Datostada MX 2026).
Entrada: datos/yucatan_subterranea_2012-2025_extracto.csv (extracto de Yucatán del archivo oficial
CONAGUA 'Calidad_del_Agua_Subterr_nea_p_2012-2025.xlsx', hoja 'CASUB 12-2025').
Salidas: datos/sitios_yucatan_limpio.csv (para Tableau), datos/resumen_*.csv, figs/*.png
Uso: python scripts/analisis.py  (desde la carpeta 02 Evidence Board)
"""
import sys, unicodedata
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
D, F = BASE / "datos", BASE / "figs"; F.mkdir(exist_ok=True)
df = pd.read_csv(D / "yucatan_subterranea_2012-2025_extracto.csv", sep=";", dtype=str, keep_default_na=False)

# ---------- verificación contra el archivo original (sumas calculadas al extraer) ----------
num = lambda s: pd.to_numeric(s, errors="coerce")
chk = {"n": len(df), "sumNO3": round(num(df.n_no3_mgL).sum(), 2), "sumCond": int(num(df.cond_uScm).sum()),
       "sumSDT": int(num(df.sdt_mgL).sum()), "cf_vacio": int((df.cf_nmp100 == "").sum()),
       "cf_<1": int(df.cf_nmp100.str.startswith("<").sum())}
esperado = {"n": 121, "sumNO3": 540.25, "sumCond": 179057, "sumSDT": 111681, "cf_vacio": 33, "cf_<1": 38}
print("verificación:", chk, "OK" if chk == esperado else f"DIFERENCIA vs {esperado}")

# ---------- limpieza ----------
def norm(s):
    s = s.strip().upper().rstrip(".")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
df["municipio_original"] = df.municipio
df["municipio"] = df.municipio.map(norm).replace({"OXKUZTCAB": "OXKUTZCAB"})
df["obs_calidad"] = ""
peto = df.sitio.str.contains("PETO") & (df.municipio == "MERIDA")
df.loc[peto, "obs_calidad"] = "Municipio registrado como MERIDA; nombre y coordenadas corresponden a Peto"
df.loc[df.municipio_original.str.strip() == "OXKUZTCAB", "obs_calidad"] = "Municipio con error de captura (OXKUZTCAB)"
for c in ["lat", "lon", "cond_uScm", "sdt_mgL", "n_no3_mgL"]:
    df[c] = num(df[c])
df["cf_dato"] = np.where(df.cf_nmp100 == "", "Sin dato", np.where(df.cf_nmp100.str.startswith("<"), "No detectado (<1)", "Detectado"))
df["cf_valor"] = num(df.cf_nmp100.str.replace("<", "", regex=False))
df.loc[df.cf_nmp100.str.startswith("<"), "cf_valor"] = 0.5  # mitad del límite de detección, solo para graficar
df["cal_cf"] = df.cal_cf.str.strip()
df["no3_cat"] = pd.cut(df.n_no3_mgL, [-1, 5, 11, 1e9], labels=["≤5 Potable-excelente", "5–11 Potable-buena", ">11 Incumple"]).astype(str)
df["no3_incumple"] = df.n_no3_mgL > 11
df["cf_incumple"] = df.cf_valor > 1000
df["cf_mayor_200"] = df.cf_valor > 200
df["sdt_incumple"] = df.sdt_mgL > 2000
df["cond_incumple"] = df.cond_uScm > 2000
df.to_csv(D / "sitios_yucatan_limpio.csv", index=False, encoding="utf-8-sig")

# ---------- resúmenes ----------
n = len(df)
cobertura = pd.DataFrame([
    ["Sitios de monitoreo en Yucatán (archivo 2012-2025)", n],
    ["  Pozos", int((df.subtipo == "POZO").sum())], ["  Cenotes", int((df.subtipo == "CENOTE").sum())],
    ["Municipios (nombres originales distintos)", df.municipio_original.nunique()],
    ["Municipios tras normalizar nombres", df.municipio.nunique()],
    ["Sitios con dato de N-NO3", int(df.n_no3_mgL.notna().sum())],
    ["Sitios con dato de coliformes fecales", int((df.cf_dato != "Sin dato").sum())],
    ["  de ellos, no detectado (<1 NMP/100 mL)", int((df.cf_dato == "No detectado (<1)").sum())],
    ["Sitios sin dato de coliformes fecales", int((df.cf_dato == "Sin dato").sum())],
    ["Sitios con observación de calidad de datos", int((df.obs_calidad != "").sum())],
    ["Sitios de Yucatán en el archivo anual 2025", 0],
], columns=["indicador", "valor"])
cobertura.to_csv(D / "resumen_cobertura.csv", index=False, encoding="utf-8-sig")

ind = pd.DataFrame([
    ["N-NO3 > 11 mg/L (incumple)", int(df.no3_incumple.sum()), int(df.n_no3_mgL.notna().sum())],
    ["N-NO3 > 5 mg/L (pierde categoría 'excelente')", int((df.n_no3_mgL > 5).sum()), int(df.n_no3_mgL.notna().sum())],
    ["Coliformes fecales > 1,000 NMP/100 mL (incumple)", int(df.cf_incumple.sum()), int((df.cf_dato != "Sin dato").sum())],
    ["Coliformes fecales > 200 NMP/100 mL (categoría 'aceptable')", int(df.cf_mayor_200.sum()), int((df.cf_dato != "Sin dato").sum())],
    ["Coliformes fecales detectados (≥ 1)", int((df.cf_dato == "Detectado").sum()), int((df.cf_dato != "Sin dato").sum())],
    ["SDT > 2,000 mg/L (incumple)", int(df.sdt_incumple.sum()), n],
    ["SDT > 1,000 mg/L (ligeramente salobre o más)", int((df.sdt_mgL > 1000).sum()), n],
    ["Conductividad > 2,000 µS/cm (incumple)", int(df.cond_incumple.sum()), n],
], columns=["indicador", "sitios", "sitios_con_dato"])
ind["porcentaje"] = (100 * ind.sitios / ind.sitios_con_dato).round(1)
ind.to_csv(D / "resumen_indicadores.csv", index=False, encoding="utf-8-sig")

sub = df[df.cf_dato != "Sin dato"].groupby("subtipo").agg(
    sitios=("clave", "count"), cf_mediana=("cf_valor", "median"),
    cf_max=("cf_valor", "max"), detectado=("cf_dato", lambda s: (s == "Detectado").sum()),
    mayor_200=("cf_mayor_200", "sum")).reset_index()
sub["no3_mediana"] = sub.subtipo.map(df.groupby("subtipo").n_no3_mgL.median())
sub.to_csv(D / "resumen_pozo_vs_cenote.csv", index=False, encoding="utf-8-sig")

sem = df.semaforo.value_counts().reindex(["VERDE", "AMARILLO", "ROJO"]).fillna(0).astype(int)
nac = pd.Series({"VERDE": 1225, "AMARILLO": 502, "ROJO": 1026})  # nacional, mismo archivo, 2,753 sitios con semáforo
semt = pd.DataFrame({"yucatan_sitios": sem, "yucatan_pct": (100 * sem / sem.sum()).round(1),
                     "nacional_sitios": nac, "nacional_pct": (100 * nac / nac.sum()).round(1)})
semt.to_csv(D / "resumen_semaforo.csv", encoding="utf-8-sig")

tops = pd.concat([
    df.nlargest(8, "n_no3_mgL").assign(ranking="N-NO3"),
    df[df.cf_dato == "Detectado"].nlargest(8, "cf_valor").assign(ranking="Coliformes fecales")])[
    ["ranking", "clave", "sitio", "municipio", "subtipo", "n_no3_mgL", "cf_nmp100", "semaforo", "contaminantes"]]
tops.to_csv(D / "resumen_sitios_prioritarios.csv", index=False, encoding="utf-8-sig")
print(cobertura.to_string(index=False)); print(ind.to_string(index=False)); print(sub.to_string(index=False)); print(semt.to_string())
print(tops.to_string(index=False))
print("municipios con >11:", df[df.no3_incumple][["sitio","municipio","n_no3_mgL","lat","lon"]].to_string(index=False))
print("mediana NO3 total", df.n_no3_mgL.median(), "p90", df.n_no3_mgL.quantile(.9))

# ---------- figuras ----------
TEAL, AMB, RED, GRAY = "#0F5E6E", "#E0A030", "#C0392B", "#8A969C"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})

# Fig 1: mapa de sitios por N-NO3
fig, ax = plt.subplots(figsize=(7.2, 4.3))
cols = {"≤5 Potable-excelente": "#7FB3C0", "5–11 Potable-buena": AMB, ">11 Incumple": RED}
for cat, c in cols.items():
    for st, mk in [("POZO", "o"), ("CENOTE", "^")]:
        s = df[(df.no3_cat == cat) & (df.subtipo == st)]
        ax.scatter(s.lon, s.lat, c=c, marker=mk, s=46 if cat != ">11 Incumple" else 90, edgecolor="white", linewidth=.6,
                   label=f"{cat} ({st.lower()})" if len(s) else None, zorder=3)
for _, r in df[df.no3_incumple].iterrows():
    ax.annotate(f"{r.municipio.title()} {r.n_no3_mgL:.1f}", (r.lon, r.lat), xytext=(6, 5), textcoords="offset points", fontsize=8, color=RED, weight="bold")
ax.scatter([-89.6237], [20.9674], marker="*", s=120, c="black", zorder=4); ax.annotate("Mérida", (-89.6237, 20.9674), xytext=(-38, -12), textcoords="offset points", fontsize=8)
ax.set_xlabel("Longitud"); ax.set_ylabel("Latitud"); ax.set_aspect("equal")
ax.set_title("Nitrógeno de nitratos (mg/L) por sitio, valor del periodo 2012–2025 (n = 121)", fontsize=10, loc="left")
ax.legend(fontsize=7, frameon=False, loc="lower right", ncol=1); ax.grid(alpha=.25)
fig.tight_layout(); fig.savefig(F / "fig1_mapa_nitratos.png", dpi=200); plt.close(fig)

# Fig 2: coliformes pozo vs cenote
fig, ax = plt.subplots(figsize=(3.6, 3.4))
d = df[df.cf_dato != "Sin dato"]
rng = np.random.default_rng(1)
for i, (st, c) in enumerate([("POZO", TEAL), ("CENOTE", AMB)]):
    s = d[d.subtipo == st]
    ax.scatter(i + rng.uniform(-.15, .15, len(s)), s.cf_valor, c=c, s=22, alpha=.85, edgecolor="white", linewidth=.4)
    ax.hlines(s.cf_valor.median(), i - .28, i + .28, color="black", lw=2)
    ax.annotate(f"mediana {s.cf_valor.median():.0f}", (i + .3, s.cf_valor.median()), fontsize=7.5, va="center")
ax.set_yscale("log"); ax.set_ylim(.3, 3000)
ax.axhline(1000, color=RED, ls="--", lw=1); ax.text(-.45, 1150, "Límite CONAGUA: 1,000", color=RED, fontsize=7, ha="left")
ax.axhline(200, color=GRAY, ls=":", lw=1); ax.text(-.45, 150, "200: pasa a «aceptable»", color=GRAY, fontsize=7, ha="left")
ax.set_xticks([0, 1]); ax.set_xticklabels([f"Pozos (n={int((d.subtipo=='POZO').sum())})", f"Cenotes (n={int((d.subtipo=='CENOTE').sum())})"])
ax.set_xlim(-.5, 1.6); ax.set_ylabel("Coliformes fecales (NMP/100 mL, log)")
ax.set_title("Coliformes fecales por tipo de sitio", fontsize=10, loc="left")
ax.text(-.5, .35, "No detectados (<1) graficados en 0.5", fontsize=6.5, color=GRAY)
fig.tight_layout(); fig.savefig(F / "fig2_coliformes_pozo_cenote.png", dpi=200); plt.close(fig)

# Fig 3: semáforo Yucatán vs nacional
fig, ax = plt.subplots(figsize=(3.6, 3.4))
x = np.arange(3); w = .38
ax.bar(x - w/2, semt.yucatan_pct, w, color=TEAL, label="Yucatán (121)")
ax.bar(x + w/2, semt.nacional_pct, w, color="#B7C7CC", label="Nacional (2,753)")
for i, (a, b) in enumerate(zip(semt.yucatan_pct, semt.nacional_pct)):
    ax.text(i - w/2, a + 1, f"{a:.0f}%", ha="center", fontsize=7.5); ax.text(i + w/2, b + 1, f"{b:.0f}%", ha="center", fontsize=7.5)
ax.set_xticks(x); ax.set_xticklabels(["Verde", "Amarillo", "Rojo"]); ax.set_ylabel("% de sitios")
ax.legend(frameon=False, fontsize=7.5); ax.set_title("Semáforo CONAGUA 2012–2025", fontsize=10, loc="left")
fig.tight_layout(); fig.savefig(F / "fig3_semaforo.png", dpi=200); plt.close(fig)

# Fig 4: salinidad (SDT) vs longitud/latitud mapa
fig, ax = plt.subplots(figsize=(3.6, 3.4))
bins = [0, 1000, 2000, 1e9]; labs = ["≤1,000 dulce", "1,000–2,000 lig. salobre", ">2,000 incumple"]; cs = ["#7FB3C0", AMB, RED]
cat = pd.cut(df.sdt_mgL, bins, labels=labs)
for l, c in zip(labs, cs):
    s = df[cat == l]; ax.scatter(s.lon, s.lat, c=c, s=22, edgecolor="white", linewidth=.4, label=f"{l} ({len(s)})")
ax.set_aspect("equal"); ax.legend(fontsize=6.5, frameon=False, loc="lower right"); ax.grid(alpha=.25)
ax.set_title("Sólidos disueltos totales (mg/L)", fontsize=10, loc="left"); ax.tick_params(labelsize=7)
fig.tight_layout(); fig.savefig(F / "fig4_salinidad.png", dpi=200); plt.close(fig)
print("figuras listas")
