"""Analisis Exploratorio (EDA) y Pruebas de Hipotesis No Parametricas para Team Sunchos.

Genera tablas estadisticas reproducibles en outputs/tables/ y figuras diagnosticas en outputs/figures/:
1. Descriptivos por Zona (24 muns., Poligono Reserva, Unidad Geo 54) y Entorno (Opcion A 2 km).
2. Mann-Whitney U + Tamano del efecto (Delta de Cliff) para H1 (Dentro vs Fuera).
3. Kruskal-Wallis + Post-hoc de Dunn (correccion Holm-Bonferroni) para Zona x Entorno y Recarga/Transito/Descarga.
4. Analisis de sensibilidad: MAUP (24 muns vs Poligono), <LD (LD/2 vs 0 vs LD), frontera estatal (121 vs 119), y umbrales buffer (10%, 20%, 30%, binario forzado).
5. Correlaciones de Spearman entre calidad hidrica y presiones (DENUE, ITER 2020, % uso de suelo, dist_costa_km).
"""
import numpy as np
import pandas as pd
import geopandas as gpd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

from config import BI_DIR, CURATED_DIR, FIG_DIR, STAGING_DIR, TAB_DIR


def cliffs_delta(x: np.ndarray, y: np.ndarray) -> float:
    """Calcula el tamano del efecto no parametrico Delta de Cliff en [-1, 1]."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    x = x[~np.isnan(x)]
    y = y[~np.isnan(y)]
    if len(x) == 0 or len(y) == 0:
        return np.nan
    diff = x[:, None] - y[None, :]
    return float((np.sum(diff > 0) - np.sum(diff < 0)) / (len(x) * len(y)))


def holm_adjust(pvals: list[float]) -> list[float]:
    """Ajuste de Holm-Bonferroni para comparaciones multiples."""
    m = len(pvals)
    order = np.argsort(pvals)
    adj = np.empty(m, dtype=float)
    running_max = 0.0
    for k, idx in enumerate(order):
        val = min(1.0, pvals[idx] * (m - k))
        running_max = max(running_max, val)
        adj[idx] = running_max
    return adj.tolist()


def dunn_posthoc_holm(df: pd.DataFrame, group_col: str, val_col: str) -> pd.DataFrame:
    """Prueba post-hoc de Dunn con correccion por empates y ajuste Holm-Bonferroni."""
    sub = df[[group_col, val_col]].dropna().copy()
    groups = sorted(sub[group_col].unique())
    n = len(sub)
    if len(groups) < 2 or n < 3:
        return pd.DataFrame()
    ranks = stats.rankdata(sub[val_col].values)
    sub["rank"] = ranks
    # Correccion por empates
    _, counts = np.unique(sub[val_col].values, return_counts=True)
    tie_corr = np.sum(counts ** 3 - counts) / (12.0 * (n - 1)) if n > 1 else 0.0
    s2 = (n * (n + 1) / 12.0) - tie_corr

    mean_ranks = sub.groupby(group_col)["rank"].mean().to_dict()
    sizes = sub.groupby(group_col)["rank"].count().to_dict()

    rows = []
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            g1, g2 = groups[i], groups[j]
            se = np.sqrt(s2 * (1.0 / sizes[g1] + 1.0 / sizes[g2]))
            z = (mean_ranks[g1] - mean_ranks[g2]) / se if se > 0 else 0.0
            p = 2.0 * (1.0 - stats.norm.cdf(abs(z)))
            rows.append(
                {
                    "grupo_1": g1,
                    "grupo_2": g2,
                    "n_1": int(sizes[g1]),
                    "n_2": int(sizes[g2]),
                    "mediana_1": round(float(sub[sub[group_col] == g1][val_col].median()), 4),
                    "mediana_2": round(float(sub[sub[group_col] == g2][val_col].median()), 4),
                    "z_dunn": round(float(z), 4),
                    "p_raw": float(p),
                }
            )
    res = pd.DataFrame(rows)
    if not res.empty:
        res["p_holm"] = holm_adjust(res["p_raw"].tolist())
        res["p_raw"] = res["p_raw"].round(6)
        res["p_holm"] = res["p_holm"].round(6)
    return res


def summarize_groups(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Resumen robusto (n, mediana, Q1, Q3, IQR, max, % rebase NOM-127) por grupo."""
    rows = []
    for keys, g in df.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        base_info = dict(zip(group_cols, keys))
        coli_valid = g["coli_fec_val_ld2"].dropna()
        coli_reb = g["rebasa_coli_nom127"].dropna()
        rows.append(
            {
                **base_info,
                "n_sitios": int(len(g)),
                "n_no3_mediana": round(float(g["n_no3_val_ld2"].median()), 3),
                "n_no3_q1": round(float(g["n_no3_val_ld2"].quantile(0.25)), 3),
                "n_no3_q3": round(float(g["n_no3_val_ld2"].quantile(0.75)), 3),
                "n_no3_max": round(float(g["n_no3_val_ld2"].max()), 3),
                "n_no3_pct_rebase": round(float(g["rebasa_n_no3_nom127"].mean() * 100), 2),
                "n_coli_validos": int(len(coli_valid)),
                "coli_mediana": round(float(coli_valid.median()), 3) if len(coli_valid) > 0 else np.nan,
                "coli_q1": round(float(coli_valid.quantile(0.25)), 3) if len(coli_valid) > 0 else np.nan,
                "coli_q3": round(float(coli_valid.quantile(0.75)), 3) if len(coli_valid) > 0 else np.nan,
                "coli_max": round(float(coli_valid.max()), 3) if len(coli_valid) > 0 else np.nan,
                "coli_pct_rebase_nom127": round(float(coli_reb.mean() * 100), 2) if len(coli_reb) > 0 else np.nan,
                "coli_pct_mayor_200": round(float((coli_valid > 200).mean() * 100), 2) if len(coli_valid) > 0 else np.nan,
                "sdt_mediana": round(float(g["sdt_val_ld2"].median()), 1),
                "sdt_iqr": round(float(g["sdt_val_ld2"].quantile(0.75) - g["sdt_val_ld2"].quantile(0.25)), 1),
                "sdt_pct_rebase": round(float(g["rebasa_sdt_nom127"].mean() * 100), 2),
                "conduct_mediana": round(float(g["conduct_val_ld2"].median()), 1),
                "dist_costa_mediana_km": round(float(g["dist_costa_km"].median()), 1),
                "pct_rojo": round(float((g["semaforo_conagua"] == "ROJO").mean() * 100), 2),
                "pct_amarillo": round(float((g["semaforo_conagua"] == "AMARILLO").mean() * 100), 2),
            }
        )
    return pd.DataFrame(rows)


def run_mw_tests(df: pd.DataFrame, split_col: str, val_a: str, val_b: str, tag: str) -> pd.DataFrame:
    """Ejecuta Mann-Whitney U + Cliff's Delta para los 4 parametros clave."""
    params = [
        ("n_no3_val_ld2", "N-NO3 (mg/L)"),
        ("coli_fec_val_ld2", "Coliformes fecales (NMP/100mL)"),
        ("sdt_val_ld2", "SDT (mg/L)"),
        ("conduct_val_ld2", "Conductividad (uS/cm)"),
    ]
    rows = []
    for col, label in params:
        a = df[df[split_col] == val_a][col].dropna().values
        b = df[df[split_col] == val_b][col].dropna().values
        u_stat, p_val = stats.mannwhitneyu(a, b, alternative="two-sided")
        d = cliffs_delta(a, b)
        rows.append(
            {
                "comparacion": tag,
                "parametro": label,
                "grupo_a": val_a,
                "n_a": int(len(a)),
                "mediana_a": round(float(np.median(a)), 3),
                "iqr_a": round(float(np.percentile(a, 75) - np.percentile(a, 25)), 3),
                "grupo_b": val_b,
                "n_b": int(len(b)),
                "mediana_b": round(float(np.median(b)), 3),
                "iqr_b": round(float(np.percentile(b, 75) - np.percentile(b, 25)), 3),
                "u_mann_whitney": round(float(u_stat), 2),
                "p_valor_bilateral": round(float(p_val), 6),
                "cliffs_delta": round(float(d), 4),
            }
        )
    return pd.DataFrame(rows)


def make_figures(sites: pd.DataFrame, mun: pd.DataFrame) -> None:
    """Genera figuras diagnosticas de alta resolucion para Evidence Board."""
    plt.rcParams["figure.dpi"] = 180
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False

    # Figura 1: Boxplots + puntos individuales por Zona (24 muns) y Entorno 2 km
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    params_fig = [
        ("n_no3_val_ld2", "N-NO3 (mg/L)", 11.0, "NOM-127: 11 mg/L"),
        ("coli_fec_val_ld2", "Coliformes fecales (NMP/100 mL, log10+1)", 200.0, "CONAGUA Aceptable: 200"),
        ("sdt_val_ld2", "Solidos Disueltos Totales (mg/L)", 1000.0, "NOM-127: 1,000 mg/L"),
        ("conduct_val_ld2", "Conductividad electrica (uS/cm)", 2000.0, "CONAGUA Riego: 2,000 uS/cm"),
    ]
    order_ent = ["Urbano", "Agricola", "Mixto (Urbano-Agricola)", "Natural / Sin presion dominante"]
    short_ent = {"Urbano": "Urbano", "Agricola": "Agricola", "Mixto (Urbano-Agricola)": "Mixto", "Natural / Sin presion dominante": "Natural"}

    for ax, (col, title, lim, lim_lbl) in zip(axes.flat, params_fig):
        data_list, labels, colors = [], [], []
        for ent in order_ent:
            for z, c in [("Dentro", "#B2182B"), ("Fuera", "#2166AC")]:
                vals = sites[(sites["entorno_2km_cat"] == ent) & (sites["zona_anillo_mun"] == z)][col].dropna().values
                if col == "coli_fec_val_ld2":
                    vals = np.log10(vals + 1.0)
                if len(vals) > 0:
                    data_list.append(vals)
                    labels.append(f"{short_ent[ent]}\n{z}\n(n={len(vals)})")
                    colors.append(c)

        bp = ax.boxplot(data_list, patch_artist=True, showfliers=False)
        for patch, c in zip(bp["boxes"], colors):
            patch.set_facecolor(c)
            patch.set_alpha(0.35)
        for median in bp["medians"]:
            median.set_color("black")
            median.set_linewidth(1.6)
        rng = np.random.default_rng(42)
        for idx, (vals, c) in enumerate(zip(data_list, colors), start=1):
            xj = rng.normal(idx, 0.07, size=len(vals))
            ax.scatter(xj, vals, color=c, s=18, alpha=0.8, zorder=3)

        lim_plot = np.log10(lim + 1.0) if col == "coli_fec_val_ld2" else lim
        ax.axhline(lim_plot, color="#D95F02", linestyle="--", linewidth=1.2, label=lim_lbl)
        if col == "coli_fec_val_ld2":
            ax.axhline(np.log10(1.1 + 1.0), color="#7570B3", linestyle=":", linewidth=1.2, label="NOM-127 Ausencia (<1.1)")
        ax.set_xticks(range(1, len(labels) + 1))
        ax.set_xticklabels(labels, fontsize=7.5)
        ax.set_title(title, fontsize=10, fontweight="bold")
        ax.legend(fontsize=7.5, loc="upper right")

    fig.suptitle("Calidad Hidrica en Yucatan (2012-2025): Dentro vs. Fuera del Anillo (Decreto 88/2025) x Entorno 2 km", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(FIG_DIR / "fig1_boxplots_zona_entorno.png")
    plt.close(fig)

    # Figura 2: Gradiente de Salinidad (SDT) vs Distancia a Costa + N-NO3 por Unidad Geohidrologica (54 muns.)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    for z, c, m in [("Dentro", "#B2182B", "o"), ("Fuera", "#2166AC", "^")]:
        sub = sites[sites["zona_anillo_mun"] == z]
        ax1.scatter(sub["dist_costa_km"], sub["sdt_val_ld2"], c=c, marker=m, alpha=0.8, label=f"{z} (n={len(sub)})", s=38)
    ax1.axhline(1000, color="#D95F02", linestyle="--", label="NOM-127: 1,000 mg/L")
    ax1.set_xlabel("Distancia a la costa del Golfo (km)")
    ax1.set_ylabel("SDT (mg/L)")
    ax1.set_title("Control Espacial: Salinidad (SDT) vs. Distancia a la Costa", fontweight="bold")
    ax1.legend(fontsize=8)

    zones_54 = ["Recarga", "Transito", "Descarga", "Fuera"]
    box54 = [sites[sites["unidad_geo_zona"] == z]["n_no3_val_ld2"].dropna().values for z in zones_54]
    bp2 = ax2.boxplot(box54, patch_artist=True, showfliers=False)
    for patch, c in zip(bp2["boxes"], ["#1B9E77", "#D95F02", "#7570B3", "#666666"]):
        patch.set_facecolor(c)
        patch.set_alpha(0.35)
    rng = np.random.default_rng(7)
    for i, vals in enumerate(box54, start=1):
        ax2.scatter(rng.normal(i, 0.06, size=len(vals)), vals, color="#333333", s=16, alpha=0.75)
    ax2.axhline(11.0, color="#B2182B", linestyle="--", label="NOM-127: 11 mg/L")
    ax2.set_xticks(range(1, 5))
    ax2.set_xticklabels([f"{z}\n(n={len(b)})" for z, b in zip(zones_54, box54)])
    ax2.set_ylabel("N-NO3 (mg/L)")
    ax2.set_title("Nitratos por Zona Hidrologica (54 muns. Decreto 88/2025)", fontweight="bold")
    ax2.legend(fontsize=8)

    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig2_gradiente_costa_y_unidad54.png")
    plt.close(fig)

    # Figura 3: Porcentaje de rebase NOM-127 por Entorno 2 km y Presion Urbana/Agricola
    fig, ax = plt.subplots(figsize=(9.5, 5))
    ent_summary = summarize_groups(sites, ["entorno_2km_cat"])
    x = np.arange(len(ent_summary))
    w = 0.25
    ax.bar(x - w, ent_summary["n_no3_pct_rebase"], width=w, label="N-NO3 > 11 mg/L", color="#D95F02")
    ax.bar(x, ent_summary["coli_pct_rebase_nom127"], width=w, label="Coliformes fecales > 0 (Ausencia)", color="#B2182B")
    ax.bar(x + w, ent_summary["sdt_pct_rebase"], width=w, label="SDT > 1,000 mg/L", color="#2166AC")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{r['entorno_2km_cat']}\n(n={r['n_sitios']})" for _, r in ent_summary.iterrows()], fontsize=8.5)
    ax.set_ylabel("% de sitios que rebasan referencia")
    ax.set_title("Frecuencia de Incumplimiento Referencial (NOM-127) por Entorno (Buffer 2 km)", fontweight="bold")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig3_rebases_por_entorno.png")
    plt.close(fig)

    # Figura 4: Mapa geohidrologico (Unidad 54, Poligono 88/2025 y sitios RENAMECA)
    mun_g = gpd.read_file(CURATED_DIR / "municipios_yucatan_curated.gpkg")
    res_g = gpd.read_file(STAGING_DIR / "reserva_anillo_cenotes_2025.gpkg")
    sites_g = gpd.read_file(CURATED_DIR / "sitios_yucatan_curated.gpkg")

    fig, ax = plt.subplots(figsize=(10.5, 5.8), dpi=220)
    zone_colors = {"Recarga": "#d9f0d3", "Transito": "#fee0b6", "Descarga": "#d1e5f0", "Fuera": "#f3f4f6"}
    mun_g["color"] = mun_g["unidad_geo_zona"].map(zone_colors).fillna("#f3f4f6")
    mun_g.plot(ax=ax, color=mun_g["color"], edgecolor="#9ca3af", linewidth=0.45, zorder=1)
    mun_g[mun_g["en_decreto_2025"]].boundary.plot(ax=ax, edgecolor="#047857", linewidth=0.95, linestyle="--", zorder=2)
    res_g.boundary.plot(ax=ax, edgecolor="#064e3b", linewidth=2.0, zorder=3)
    res_g.plot(ax=ax, facecolor="#10b981", alpha=0.14, zorder=2)

    sem_colors = {"VERDE": "#16a34a", "AMARILLO": "#f59e0b", "ROJO": "#dc2626"}
    for tipo, marker, size in [("POZO", "o", 36), ("CENOTE", "D", 54)]:
        for sem, col in sem_colors.items():
            sub = sites_g[(sites_g["tipo_sitio"] == tipo) & (sites_g["semaforo_conagua"] == sem)]
            if not sub.empty:
                sub.plot(ax=ax, color=col, marker=marker, markersize=size, edgecolor="#111827", linewidth=0.6, zorder=4 if tipo == "POZO" else 5)

    ref_muns = {
        "Mérida": (-16000, 14000), "Homún": (24000, -16000), "Progreso": (-15000, 12000),
        "Valladolid": (0, 14000), "Tizimín": (0, 10000), "Tekax": (28000, 14000), "Chemax": (0, 12000),
    }
    for name, (dx, dy) in ref_muns.items():
        sub_m = mun_g[mun_g["NOMGEO"] == name]
        if not sub_m.empty:
            c = sub_m.geometry.iloc[0].representative_point()
            ax.text(c.x + dx, c.y + dy, name, fontsize=7.3, fontweight="bold", color="#1f2937", ha="center", zorder=6,
                    bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="none", alpha=0.78))

    s_bounds = sites_g.total_bounds
    ax.set_xlim(s_bounds[0] - 25000, s_bounds[2] + 22000)
    ax.set_ylim(s_bounds[1] - 42000, s_bounds[3] + 28000)
    legend_items = [
        Patch(facecolor="#d9f0d3", edgecolor="#9ca3af", label="Unidad 54: Recarga (n=18 sitios)"),
        Patch(facecolor="#fee0b6", edgecolor="#9ca3af", label="Unidad 54: Tránsito (n=59 sitios)"),
        Patch(facecolor="#d1e5f0", edgecolor="#9ca3af", label="Unidad 54: Descarga (n=7 sitios)"),
        Patch(facecolor="#f3f4f6", edgecolor="#9ca3af", label="Fuera Unidad 54 (n=37 sitios)"),
        Line2D([0], [0], color="#064e3b", lw=2.0, label="Polígono Reserva 88/2025 (213,763 ha)"),
        Line2D([0], [0], color="#047857", lw=1.0, ls="--", label="Límite 24 municipios Decreto 88/2025"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#16a34a", markeredgecolor="#111827", markersize=6.5, label="Pozo · Semáforo Verde (68 total)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#f59e0b", markeredgecolor="#111827", markersize=6.5, label="Pozo · Semáforo Amarillo (48 total)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#dc2626", markeredgecolor="#111827", markersize=6.5, label="Pozo · Semáforo Rojo (5 total)"),
        Line2D([0], [0], marker="D", color="w", markerfacecolor="#6b7280", markeredgecolor="#111827", markersize=6.5, label="Cenote (n=8, 100% >0 coliformes)"),
    ]
    ax.legend(handles=legend_items, loc="lower left", fontsize=7.0, frameon=True, facecolor="white", framealpha=0.95, ncol=2).set_zorder(10)
    ax.set_title("Mapa Base Geohidrológico: Reserva Anillo de Cenotes (88/2025), Unidad 54 y Red RENAMECA (n=121)", fontsize=10.5, fontweight="bold", pad=6)
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig4_mapa_anillo_calidad.png", dpi=220)
    plt.close(fig)

    # Figura 5: Contraste estructural Cenote vs Pozo (Coliformes y Nitratos)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.6, 3.8), dpi=220)
    rng = np.random.default_rng(12)
    c_cen = np.log10(sites[sites["tipo_sitio"] == "CENOTE"]["coli_fec_val_ld2"].dropna().values + 1.0)
    c_poz = np.log10(sites[sites["tipo_sitio"] == "POZO"]["coli_fec_val_ld2"].dropna().values + 1.0)
    bp1 = ax1.boxplot([c_cen, c_poz], patch_artist=True, showfliers=False, widths=0.45)
    for patch, col in zip(bp1["boxes"], ["#dc2626", "#2563eb"]):
        patch.set_facecolor(col)
        patch.set_alpha(0.32)
    for m in bp1["medians"]:
        m.set_color("black")
        m.set_linewidth(1.8)
    for i, (vals, col) in enumerate([(c_cen, "#dc2626"), (c_poz, "#2563eb")], start=1):
        ax1.scatter(rng.normal(i, 0.055, size=len(vals)), vals, color=col, s=22, alpha=0.8, zorder=3)
    ax1.axhline(np.log10(1.1 + 1.0), color="#6d28d9", ls=":", lw=1.2, label="NOM-127 Ausencia (<1.1)")
    ax1.axhline(np.log10(200.0 + 1.0), color="#d97706", ls="--", lw=1.2, label="CONAGUA Aceptable (200)")
    ax1.set_ylim(-0.02, 2.95)
    ax1.set_xticks([1, 2])
    ax1.set_xticklabels([f"CENOTE (n={len(c_cen)})\nMediana: 256.4\n100% rebasa", f"POZO (n={len(c_poz)})\nMediana: 2.0\n52.5% rebasa"], fontsize=8.5)
    ax1.set_ylabel("Coliformes fecales (log10[NMP/100mL + 1])", fontsize=8.5)
    ax1.set_title("A) Coliformes: Cenote >> Pozo (p = 0.000013, Δ = +0.903)", fontsize=9.2, fontweight="bold")
    ax1.legend(fontsize=7.3, loc="upper right")

    n_cen = sites[sites["tipo_sitio"] == "CENOTE"]["n_no3_val_ld2"].dropna().values
    n_poz = sites[sites["tipo_sitio"] == "POZO"]["n_no3_val_ld2"].dropna().values
    bp2 = ax2.boxplot([n_cen, n_poz], patch_artist=True, showfliers=False, widths=0.45)
    for patch, col in zip(bp2["boxes"], ["#dc2626", "#2563eb"]):
        patch.set_facecolor(col)
        patch.set_alpha(0.32)
    for m in bp2["medians"]:
        m.set_color("black")
        m.set_linewidth(1.8)
    for i, (vals, col) in enumerate([(n_cen, "#dc2626"), (n_poz, "#2563eb")], start=1):
        ax2.scatter(rng.normal(i, 0.055, size=len(vals)), vals, color=col, s=22, alpha=0.8, zorder=3)
    ax2.axhline(11.0, color="#b91c1c", ls="--", lw=1.2, label="NOM-127: 11 mg/L")
    ax2.set_ylim(-0.5, 15.6)
    ax2.set_xticks([1, 2])
    ax2.set_xticklabels([f"CENOTE (n={len(n_cen)})\nMediana: 1.13 mg/L\n0% rebasa", f"POZO (n={len(n_poz)})\nMediana: 4.51 mg/L\n2.65% rebasa"], fontsize=8.5)
    ax2.set_ylabel("N-NO3 (mg/L)", fontsize=8.5)
    ax2.set_title("B) Nitratos: Pozo >> Cenote (p = 0.000316, Δ = -0.712)", fontsize=9.2, fontweight="bold")
    ax2.legend(fontsize=7.3, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig5_cenote_vs_pozo.png", dpi=220)
    plt.close(fig)


def main() -> None:
    sites = pd.read_csv(BI_DIR / "dim_sitio.csv")
    fact = pd.read_csv(BI_DIR / "fact_calidad_sitio.csv")
    mun = pd.read_csv(BI_DIR / "dim_municipio.csv")

    # 1. Tablas descriptivas
    res_mun24 = summarize_groups(sites, ["zona_anillo_mun"])
    res_polig = summarize_groups(sites, ["zona_anillo_poligono"])
    res_geo54 = summarize_groups(sites, ["unidad_geo_zona"])
    res_entorno = summarize_groups(sites, ["entorno_2km_cat"])
    res_cruzado = summarize_groups(sites, ["zona_anillo_mun", "entorno_2km_cat"])
    res_subtipo = summarize_groups(sites, ["tipo_sitio"])

    res_mun24.to_csv(TAB_DIR / "eda_resumen_mun24.csv", index=False, encoding="utf-8-sig")
    res_polig.to_csv(TAB_DIR / "eda_resumen_poligono.csv", index=False, encoding="utf-8-sig")
    res_geo54.to_csv(TAB_DIR / "eda_resumen_unidad_geo54.csv", index=False, encoding="utf-8-sig")
    res_entorno.to_csv(TAB_DIR / "eda_resumen_entorno_2km.csv", index=False, encoding="utf-8-sig")
    res_cruzado.to_csv(TAB_DIR / "eda_resumen_mun24_x_entorno.csv", index=False, encoding="utf-8-sig")
    res_subtipo.to_csv(TAB_DIR / "eda_resumen_pozo_vs_cenote.csv", index=False, encoding="utf-8-sig")

    # 2. Pruebas Mann-Whitney U (H1: Dentro vs Fuera bajo multiples definiciones + sensibilidad)
    mw_all = pd.concat(
        [
            run_mw_tests(sites, "zona_anillo_mun", "Dentro", "Fuera", "Primaria: 24 Municipios (n=121)"),
            run_mw_tests(sites[sites["dentro_poligono_yucatan"]], "zona_anillo_mun", "Dentro", "Fuera", "Sensibilidad Frontera: 24 Muns. (n=119)"),
            run_mw_tests(sites, "zona_anillo_poligono", "Dentro Reserva", "Fuera Reserva", "Sensibilidad MAUP: Poligono Reserva (n=121)"),
            run_mw_tests(sites, "tipo_sitio", "CENOTE", "POZO", "Contraste Estructural: Cenote vs Pozo"),
        ],
        ignore_index=True,
    )
    mw_all.to_csv(TAB_DIR / "eda_mann_whitney_resultados.csv", index=False, encoding="utf-8-sig")

    # 3. Sensibilidad <LD para Coliformes Fecales (LD/2 vs 0 vs LD)
    coli_fact = fact[fact["param_code"] == "COLI_FEC"].merge(
        sites[["site_id", "zona_anillo_mun", "zona_anillo_poligono", "entorno_2km_cat"]], on="site_id"
    )
    sens_ld_rows = []
    for col_val, label in [("valor_ld2", "LD/2 (0.5)"), ("valor_zero", "Cero (0.0)"), ("valor_ld", "LD (1.0)")]:
        a = coli_fact[coli_fact["zona_anillo_mun"] == "Dentro"][col_val].values
        b = coli_fact[coli_fact["zona_anillo_mun"] == "Fuera"][col_val].values
        u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
        sens_ld_rows.append(
            {
                "regla_censura": label,
                "mediana_dentro": round(float(np.median(a)), 3),
                "mediana_fuera": round(float(np.median(b)), 3),
                "u_stat": round(float(u), 2),
                "p_valor": round(float(p), 6),
                "cliffs_delta": round(cliffs_delta(a, b), 4),
            }
        )
    pd.DataFrame(sens_ld_rows).to_csv(TAB_DIR / "eda_sensibilidad_ld_coliformes.csv", index=False, encoding="utf-8-sig")

    # 4. Kruskal-Wallis + Dunn post-hoc para Entorno 2 km y Unidad Geohidrologica (54 muns.)
    kw_rows = []
    dunn_frames = []
    for grp_col, grp_label in [("entorno_2km_cat", "Entorno 2km (Opcion A)"), ("unidad_geo_zona", "Unidad Geo 54 (Recarga/Transito/Descarga/Fuera)")]:
        for param_col, p_label in [
            ("n_no3_val_ld2", "N-NO3"),
            ("coli_fec_val_ld2", "Coliformes fecales"),
            ("sdt_val_ld2", "SDT"),
            ("conduct_val_ld2", "Conductividad"),
        ]:
            sub = sites[[grp_col, param_col]].dropna()
            groups_data = [g[param_col].values for _, g in sub.groupby(grp_col)]
            if len(groups_data) >= 2:
                h_stat, p_kw = stats.kruskal(*groups_data)
                kw_rows.append(
                    {
                        "factor": grp_label,
                        "parametro": p_label,
                        "k_grupos": len(groups_data),
                        "n_total": int(len(sub)),
                        "h_kruskal": round(float(h_stat), 4),
                        "p_valor_kw": round(float(p_kw), 6),
                    }
                )
                if p_kw < 0.10:
                    d_df = dunn_posthoc_holm(sub, grp_col, param_col)
                    d_df.insert(0, "parametro", p_label)
                    d_df.insert(0, "factor", grp_label)
                    dunn_frames.append(d_df)

    pd.DataFrame(kw_rows).to_csv(TAB_DIR / "eda_kruskal_wallis.csv", index=False, encoding="utf-8-sig")
    if dunn_frames:
        pd.concat(dunn_frames, ignore_index=True).to_csv(TAB_DIR / "eda_dunn_posthoc.csv", index=False, encoding="utf-8-sig")

    # 5. Correlaciones de Spearman entre calidad hidrica y variables espaciales/socio-economicas
    sites_mun = sites.merge(mun[["cve_mun", "pct_drenaje_2020", "pct_sin_drenaje_2020", "pct_letrina_2020", "densidad_pob_km2"]], on="cve_mun", how="left")
    covars = [
        "dist_costa_km", "dist_reserva_km",
        "pct_urbano_2km", "pct_agropecuario_2km", "pct_natural_2km",
        "n_denue_total_2km", "n_denue_industria_2km", "n_denue_turismo_alim_2km",
        "pob_loc_2km", "pob_loc_5km", "viv_nodren_loc_5km", "pct_nodren_loc_5km",
        "pct_drenaje_2020", "pct_sin_drenaje_2020", "pct_letrina_2020", "densidad_pob_km2",
    ]
    corr_rows = []
    for y_col, y_lbl in [("n_no3_val_ld2", "N-NO3"), ("coli_fec_val_ld2", "Coliformes"), ("sdt_val_ld2", "SDT"), ("conduct_val_ld2", "Conductividad")]:
        for x_col in covars:
            sub = sites_mun[[y_col, x_col]].dropna()
            rho, p = stats.spearmanr(sub[x_col], sub[y_col])
            corr_rows.append(
                {
                    "variable_hidrica": y_lbl,
                    "covariable_presion": x_col,
                    "n": int(len(sub)),
                    "spearman_rho": round(float(rho), 4),
                    "p_valor": round(float(p), 6),
                }
            )
    pd.DataFrame(corr_rows).to_csv(TAB_DIR / "eda_correlaciones_spearman.csv", index=False, encoding="utf-8-sig")

    # 5b. Sensibilidad de umbrales del buffer 2 km (10%, 20% Opcion A, 30%, binario forzado)
    sens_ent_rows = []
    for col_ent, esquema in [
        ("entorno_2km_cat", "Opcion A (20%)"),
        ("entorno_2km_t10", "Sensibilidad (10%)"),
        ("entorno_2km_t30", "Sensibilidad (30%)"),
        ("entorno_2km_forzado_bin", "Binario forzado (sin Natural/Mixto)"),
    ]:
        dist_counts = sites[col_ent].value_counts().to_dict()
        for param_col, p_lbl in [
            ("n_no3_val_ld2", "N-NO3"),
            ("coli_fec_val_ld2", "Coliformes fecales"),
            ("sdt_val_ld2", "SDT"),
            ("conduct_val_ld2", "Conductividad"),
        ]:
            sub = sites[[col_ent, param_col]].dropna()
            groups_data = [g[param_col].values for _, g in sub.groupby(col_ent)]
            if len(groups_data) >= 2:
                h_stat, p_kw = stats.kruskal(*groups_data)
                sens_ent_rows.append(
                    {
                        "esquema": esquema,
                        "columna": col_ent,
                        "conteo_categorias": str(dist_counts),
                        "parametro": p_lbl,
                        "k_grupos": len(groups_data),
                        "n_total": int(len(sub)),
                        "h_kruskal": round(float(h_stat), 4),
                        "p_valor_kw": round(float(p_kw), 6),
                    }
                )
    pd.DataFrame(sens_ent_rows).to_csv(TAB_DIR / "eda_sensibilidad_entorno.csv", index=False, encoding="utf-8-sig")

    # 6. Figuras
    make_figures(sites, mun)
    print(f"[05] EDA completado. Tablas en {TAB_DIR} y figuras en {FIG_DIR}.")


if __name__ == "__main__":
    main()
