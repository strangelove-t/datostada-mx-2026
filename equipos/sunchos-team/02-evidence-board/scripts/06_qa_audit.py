"""Auditoria automatizada de Calidad de Datos (QA/QC Gates) y trazabilidad SHA-256."""
import hashlib
import json
from pathlib import Path

import pandas as pd
import geopandas as gpd

from config import BI_DIR, OUTPUT_DIR, RAW_DIR, FIG_DIR, TAB_DIR


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_check(name: str, passed: bool, detail: str) -> dict:
    return {"gate": name, "passed": bool(passed), "detail": detail}


def main() -> None:
    dim_sitio = pd.read_csv(BI_DIR / "dim_sitio.csv", dtype={"cve_mun": str})
    dim_mun = pd.read_csv(BI_DIR / "dim_municipio.csv", dtype={"cve_mun": str})
    dim_param = pd.read_csv(BI_DIR / "dim_parametro.csv")
    fact = pd.read_csv(BI_DIR / "fact_calidad_sitio.csv", dtype={"cve_mun": str})

    checks: list[dict] = []

    # 1. Unicidad y nulidad de llaves primarias
    checks.append(
        run_check(
            "PK dim_sitio (site_id unico, n=121)",
            dim_sitio["site_id"].notna().all() and dim_sitio["site_id"].is_unique and len(dim_sitio) == 121,
            f"n={len(dim_sitio)}, unique={dim_sitio['site_id'].nunique()}, nulls={int(dim_sitio['site_id'].isna().sum())}",
        )
    )
    checks.append(
        run_check(
            "PK dim_municipio (cve_mun unico, n=106)",
            dim_mun["cve_mun"].notna().all() and dim_mun["cve_mun"].is_unique and len(dim_mun) == 106,
            f"n={len(dim_mun)}, unique={dim_mun['cve_mun'].nunique()}, nulls={int(dim_mun['cve_mun'].isna().sum())}",
        )
    )
    checks.append(
        run_check(
            "PK dim_parametro (param_code unico, n=4)",
            dim_param["param_code"].notna().all() and dim_param["param_code"].is_unique and len(dim_param) == 4,
            f"n={len(dim_param)}, codes={dim_param['param_code'].tolist()}",
        )
    )
    checks.append(
        run_check(
            "PK fact_calidad_sitio (fact_id unico, n=451)",
            fact["fact_id"].notna().all() and fact["fact_id"].is_unique and len(fact) == 451,
            f"n={len(fact)}, unique={fact['fact_id'].nunique()}, nulls={int(fact['fact_id'].isna().sum())}",
        )
    )

    # 2. Integridad referencial del Modelo Estrella
    checks.append(
        run_check(
            "FK fact.site_id -> dim_sitio.site_id",
            set(fact["site_id"]).issubset(set(dim_sitio["site_id"])),
            f"huerfanos={len(set(fact['site_id']) - set(dim_sitio['site_id']))}",
        )
    )
    checks.append(
        run_check(
            "FK fact.param_code -> dim_parametro.param_code",
            set(fact["param_code"]).issubset(set(dim_param["param_code"])),
            f"huerfanos={len(set(fact['param_code']) - set(dim_param['param_code']))}",
        )
    )
    checks.append(
        run_check(
            "FK dim_sitio.cve_mun -> dim_municipio.cve_mun",
            dim_sitio["cve_mun"].notna().all() and set(dim_sitio["cve_mun"]).issubset(set(dim_mun["cve_mun"])),
            f"nulls={int(dim_sitio['cve_mun'].isna().sum())}, huerfanos={len(set(dim_sitio['cve_mun']) - set(dim_mun['cve_mun']))}",
        )
    )
    n_mun_sum = int(dim_mun["n_sitios_renameca"].sum())
    n_inside_yuc = int(dim_sitio["dentro_poligono_yucatan"].sum())
    checks.append(
        run_check(
            "Consistencia conteo municipal (solo sitios dentro poligono INEGI Yucatan)",
            n_mun_sum == n_inside_yuc == 119,
            f"sum(dim_municipio.n_sitios_renameca)={n_mun_sum}, dim_sitio[dentro_poligono_yucatan]={n_inside_yuc}",
        )
    )

    # 3. Integridad geoespacial y rango fisico
    lat_ok = bool(dim_sitio["latitud"].between(19.5, 21.7).all())
    lon_ok = bool(dim_sitio["longitud"].between(-90.6, -87.3).all())
    dist_ok = bool((dim_sitio["dist_costa_km"] >= 0).all() and (dim_sitio["dist_reserva_km"] >= 0).all())
    checks.append(
        run_check(
            "Coordenadas en bounding box Yucatan y distancias >= 0",
            lat_ok and lon_ok and dist_ok,
            f"lat=[{dim_sitio['latitud'].min():.4f}, {dim_sitio['latitud'].max():.4f}], lon=[{dim_sitio['longitud'].min():.4f}, {dim_sitio['longitud'].max():.4f}]",
        )
    )

    # 4. Invariante de composicion de uso de suelo en buffer 2 km
    lu_sum = dim_sitio["pct_urbano_2km"] + dim_sitio["pct_agropecuario_2km"] + dim_sitio["pct_natural_2km"]
    lu_ok = bool(lu_sum.between(99.9, 100.1).all())
    checks.append(
        run_check(
            "Suma de usos de suelo terrestres (Urbano+Agro+Natural = 100% +/- 0.1)",
            lu_ok,
            f"min={lu_sum.min():.2f}%, max={lu_sum.max():.2f}%",
        )
    )

    # 5. QC fisicoquimico SDT/Conductividad (descarta error de unidad mS/cm vs uS/cm)
    qc_ok = bool(dim_sitio["qc_sdt_conduct_ok"].all())
    rmin, rmax = float(dim_sitio["ratio_sdt_conduct"].min()), float(dim_sitio["ratio_sdt_conduct"].max())
    checks.append(
        run_check(
            "QC fisicoquimico SDT / Conductividad en rango valido [0.40, 0.80]",
            qc_ok and 0.40 <= rmin and rmax <= 0.80,
            f"qc_all_true={qc_ok}, rango=[{rmin:.4f}, {rmax:.4f}]",
        )
    )

    # 6. Consistencia de censura <LD vs rebases NOM-127 y consistencia dim_sitio vs fact
    cens_reb = fact[(fact["is_censored"] == True) & (fact["rebasa_referencia"] == True)]
    checks.append(
        run_check(
            "Cero valores censurados (<LD) marcados falsamente como rebase",
            len(cens_reb) == 0,
            f"casos={len(cens_reb)}",
        )
    )
    reb_counts = fact[fact["rebasa_referencia"] == True].groupby("param_code").size().to_dict()
    dim_n_no3 = int(dim_sitio["rebasa_n_no3_nom127"].sum())
    dim_coli = int(dim_sitio["rebasa_coli_nom127"].dropna().sum())
    dim_sdt = int(dim_sitio["rebasa_sdt_nom127"].sum())
    checks.append(
        run_check(
            "Consistencia de conteo de rebases entre fact_calidad_sitio y dim_sitio",
            reb_counts.get("N_NO3", 0) == dim_n_no3 == 3
            and reb_counts.get("COLI_FEC", 0) == dim_coli == 50
            and reb_counts.get("SDT", 0) == dim_sdt == 29,
            f"fact={reb_counts}, dim=(N_NO3:{dim_n_no3}, COLI_FEC:{dim_coli}, SDT:{dim_sdt})",
        )
    )

    # 7. Capas GeoJSON validas para Tableau
    geo_details = []
    geo_ok = True
    for gname in ["municipios_yucatan.geojson", "reserva_anillo_cenotes_2025.geojson", "sitios_yucatan.geojson"]:
        gp = BI_DIR / gname
        if not gp.exists():
            geo_ok = False
            geo_details.append(f"{gname}: MISSING")
            continue
        gdf = gpd.read_file(gp)
        valid_geoms = bool(gdf.geometry.is_valid.all())
        geo_ok = geo_ok and valid_geoms and len(gdf) > 0
        geo_details.append(f"{gname}(n={len(gdf)}, valid={valid_geoms})")
    checks.append(run_check("Capas GeoJSON listas para Tableau", geo_ok, " | ".join(geo_details)))

    # 8. Inmutabilidad de 01_raw contra MANIFEST_FUENTES.csv (SHA-256)
    manifest = pd.read_csv(RAW_DIR / "MANIFEST_FUENTES.csv")
    sha_col = [c for c in manifest.columns if "sha" in c.lower()][0]
    path_col = [c for c in manifest.columns if "ruta" in c.lower() or "archivo" in c.lower()][0]
    sha_mismatches = 0
    sha_checked = 0
    for _, row in manifest.iterrows():
        rel_path = Path(str(row[path_col]))
        candidate = RAW_DIR / rel_path
        if not candidate.exists():
            # Intentar resolver desde raiz del proyecto si la ruta incluye equipos/...
            candidate = RAW_DIR.parent.parent.parent.parent / rel_path
        if candidate.exists():
            sha_checked += 1
            if sha256_file(candidate).lower() != str(row[sha_col]).strip().lower():
                sha_mismatches += 1
    checks.append(
        run_check(
            "Inmutabilidad 01_raw verificada por SHA-256 vs MANIFEST_FUENTES.csv",
            sha_checked == len(manifest) and sha_mismatches == 0,
            f"verificados={sha_checked}/{len(manifest)}, discrepancias={sha_mismatches}",
        )
    )

    # 9. Existencia de tablas EDA y figuras
    expected_figs = [
        "fig1_boxplots_zona_entorno.png",
        "fig2_gradiente_costa_y_unidad54.png",
        "fig3_rebases_por_entorno.png",
        "fig4_mapa_anillo_calidad.png",
        "fig5_cenote_vs_pozo.png",
    ]
    missing_figs = [f for f in expected_figs if not (FIG_DIR / f).exists()]
    tab_count = len(list(TAB_DIR.glob("*.csv")))
    checks.append(
        run_check(
            "Artefactos EDA generados (tablas CSV y figuras PNG)",
            len(missing_figs) == 0 and tab_count >= 12,
            f"tablas_csv={tab_count}, figuras_faltantes={missing_figs}",
        )
    )

    all_passed = all(c["passed"] for c in checks)
    report = {
        "all_passed": all_passed,
        "total_gates": len(checks),
        "passed_gates": sum(1 for c in checks if c["passed"]),
        "failed_gates": sum(1 for c in checks if not c["passed"]),
        "checks": checks,
    }
    with open(BI_DIR / "qa_audit_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    md_lines = [
        "# QA/QC Audit Report — Team Sunchos (Fase 02 Explore)\n",
        f"- **Estado Global:** {'PASS (100%)' if all_passed else 'FAIL'}",
        f"- **Compuertas aprobadas:** {report['passed_gates']} / {report['total_gates']}\n",
        "| Gate | Estado | Evidencia verificada |",
        "|---|---|---|",
    ]
    for c in checks:
        status = "PASS" if c["passed"] else "FAIL"
        md_lines.append(f"| {c['gate']} | **{status}** | `{c['detail']}` |")
    with open(OUTPUT_DIR / "QA_REPORT.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")

    print(f"[06] QA/QC completado: {report['passed_gates']}/{report['total_gates']} compuertas PASS.")
    if not all_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

