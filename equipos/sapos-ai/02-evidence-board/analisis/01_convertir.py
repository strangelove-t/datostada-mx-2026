"""Convierte Subterraneo.xlsb (RENAMECA, CONAGUA) a CSV sin alterar valores."""
import sys
import pandas as pd

origen, destino = sys.argv[1], sys.argv[2]
for hoja, nombre in [("SITIOS", "sitios"), ("RESULTADOS", "resultados"), (2, "simbologia")]:
    df = pd.read_excel(origen, sheet_name=hoja, engine="pyxlsb", dtype=object)
    df.to_csv(f"{destino}/{nombre}_nacional.csv", index=False, encoding="utf-8-sig")
    print(nombre, df.shape)
