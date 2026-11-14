"""Orquestador reproducible completo del pipeline ETL + GIS + BI + EDA + QA (Fase 02)."""
import subprocess
import sys
from pathlib import Path

SCRIPTS = [
    "01_build_gis_layers.py",
    "02_clean_renameca.py",
    "03_spatial_enrichment.py",
    "04_build_bi_model.py",
    "05_eda_hypothesis.py",
    "06_qa_audit.py",
]


def main() -> None:
    scripts_dir = Path(__file__).resolve().parent
    for script in SCRIPTS:
        script_path = scripts_dir / script
        print(f"=== Ejecutando {script} ===")
        res = subprocess.run([sys.executable, str(script_path)], check=False)
        if res.returncode != 0:
            raise SystemExit(f"Fallo {script} con codigo {res.returncode}")
    print("=== Pipeline completo ejecutado exitosamente (01 -> 06) ===")


if __name__ == "__main__":
    main()

