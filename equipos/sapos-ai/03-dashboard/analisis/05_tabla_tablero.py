"""Arma la tabla única del tablero y la escribe como Excel y, si está instalado tableauhyperapi, como extracto Hyper.

Uso: python 05_tabla_tablero.py <datos-derivados> <geojson de la península> <carpeta de salida>

Filas de tipo «muestreo»: una por muestreo (683), con los atributos de su sitio repetidos.
Filas de tipo «contorno»: los vértices del límite de Yucatán, repetidos para cada municipio y
cada clase, de modo que el contorno siga visible cuando el tablero se filtra.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
PROC = RAIZ / "datos-procesados"
BUILD = RAIZ / "tablero" / "build"
GEOJSON = RAIZ / "datos-crudos" / "geo" / "peninsula.geojson"

MUNICIPIOS = {
    "ABALA": "Abalá", "ACANCEH": "Acanceh", "AKIL": "Akil", "CACALCHEN": "Cacalchén", "CANSAHCAB": "Cansahcab", "CELESTUN": "Celestún",
    "CHAPAB": "Chapab", "CHEMAX": "Chemax", "CHICXULUB PUEBLO": "Chicxulub Pueblo", "CHOCHOLA": "Chocholá", "CONKAL": "Conkal",
    "CUZAMA": "Cuzamá", "DZAN": "Dzan", "DZITAS": "Dzitás", "ESPITA": "Espita", "HALACHO": "Halachó", "HOCABA": "Hocabá", "HOCTUN": "Hoctún",
    "HOMUN": "Homún", "HUHI": "Huhí", "HUNUCMA": "Hunucmá", "IZAMAL": "Izamal", "KANASIN": "Kanasín", "KINCHIL": "Kinchil", "KOPOMA": "Kopomá",
    "MANI": "Maní", "MAXCANU": "Maxcanú", "MERIDA": "Mérida", "MOTUL": "Motul", "MUNA": "Muna", "MUXUPIP": "Muxupip", "OPICHEN": "Opichén",
    "OXKUZTCAB": "Oxkutzcab", "PETO": "Peto", "PROGRESO": "Progreso", "SAMAHIL": "Samahil", "SOTUTA": "Sotuta", "SUMA": "Suma", "TAHDZIU": "Tahdziú",
    "TAHMEK": "Tahmek", "TEABO": "Teabo", "TECOH": "Tecoh", "TEKAL DE VENEGAS": "Tekal de Venegas", "TEKANTO": "Tekantó", "TEKAX": "Tekax",
    "TEKIT": "Tekit", "TELCHAC PUEBLO": "Telchac Pueblo", "TEMAX": "Temax", "TEMOZON": "Temozón", "TEPAKAN": "Tepakán", "TETIZ": "Tetiz",
    "TICUL": "Ticul", "TIMUCUY": "Timucuy", "TINUM": "Tinum", "TIXKOKOB": "Tixkokob", "TIXPEHUAL": "Tixpéhual", "TIZIMIN": "Tizimín",
    "TUNKAS": "Tunkás", "TZUCACAB": "Tzucacab", "UAYMA": "Uayma", "UMAN": "Umán", "VALLADOLID": "Valladolid", "XOCCHEL": "Xocchel",
    "YAXCABA": "Yaxcabá", "YAXKUKUL": "Yaxkukul",
}
ATENDER = ["Sales o dureza", "Bacterias", "Ambos", "Ninguno recurrente"]
# La fuente asigna a Mérida un pozo del sistema de agua potable de Peto; su nombre y sus coordenadas lo ubican en Peto.
CORRECCION_MUNICIPIO = {"OCPYU5381": "PETO"}

# (nombre, tipo): mismo orden en Excel, Hyper y libro de Tableau
COLUMNAS = [
    ("tipo", "string"), ("clave", "string"), ("sitio", "string"), ("municipio", "string"), ("subtipo", "string"), ("atender", "string"),
    ("pos_x", "real"), ("pos_y", "real"), ("borde_y", "real"), ("sitio_x", "real"), ("orden_borde", "integer"), ("poligono", "string"),
    ("fecha", "date"), ("anio", "integer"), ("sdt", "real"), ("dureza", "real"), ("coliformes", "real"),
    ("sal_exc", "integer"), ("dur_exc", "integer"), ("bac_det", "integer"), ("bac_mil", "integer"), ("uno", "integer"),
    ("muestreos_sitio", "integer"), ("anios_sitio", "integer"), ("orden_po", "integer"), ("sal_movil", "real"), ("bac_movil", "real"),
    ("estado_sal", "string"), ("estado_bac", "string"), ("mun_etiqueta", "string"), ("mun_orden", "integer"),
    ("atender_desc", "string"), ("con_bac", "string"), ("sal_texto", "string"), ("dur_texto", "string"), ("bac_texto", "string"),
    ("anio_txt", "string"), ("atender_x", "real"), ("orden_inv", "integer"), ("clase", "string"), ("rotulo", "string"), ("periodo_texto", "string"),
]
ROTULOS = ["Mérida", "Progreso", "Celestún", "Valladolid", "Tizimín", "Tekax", "Izamal", "Maxcanú"]
DESCRIPCION = {
    "Sales o dureza": "en la mitad o más de sus muestreos",
    "Bacterias": "coliformes fecales en la mitad o más",
    "Ambos": "sales o dureza y coliformes fecales",
    "Ninguno recurrente": "nada llega a la mitad en lo medido",
}


MINUSCULAS = {"De", "Del", "La", "Las", "El", "Los", "Y", "A", "En", "Al"}
SIGLAS = {"Uady": "UADY", "Cna": "CNA", "Ii": "II", "Iii": "III", "Japay": "JAPAY", "(Japay)": "(JAPAY)", "Cfe": "CFE", "Imss": "IMSS", "Iv": "IV", "Sap": "SAP", "Gp-088": "GP-088", "Gp-104": "GP-104"}


def nombre(texto):
    """Nombre del sitio en mayúsculas y minúsculas, sin cambiar sus palabras."""
    palabras = str(texto).strip().rstrip(".").title().split()
    return " ".join(SIGLAS.get(p, p.lower() if i and p in MINUSCULAS else p) for i, p in enumerate(palabras))


def tabla(proc=PROC, geojson=GEOJSON):
    proc = Path(proc)
    s = pd.read_csv(proc / "sitios_resumen.csv")
    r = pd.read_csv(proc / "resultados_yucatan.csv", dtype=str, low_memory=False)
    sa = pd.read_csv(proc / "sitio_anio.csv")
    s["MUNICIPIO"] = s["CLAVE SITIO"].map(CORRECCION_MUNICIPIO).fillna(s["MUNICIPIO"])
    assert len(s) == 121 and len(r) == 683 and set(s["MUNICIPIO"]) == set(MUNICIPIOS)

    s = s.sort_values("lon").reset_index(drop=True)
    s["orden_po"] = np.arange(1, len(s) + 1)
    s["sal_movil"] = (s["SDT_pct"] / 100).rolling(17, center=True, min_periods=8).mean()
    med = s[s["COLI_FEC_n"] > 0]
    s["bac_movil"] = (med["COLI_FEC_pct"] / 100).rolling(17, center=True, min_periods=8).mean()
    s["municipio"] = s["MUNICIPIO"].map(MUNICIPIOS)
    s["sitio"] = s["NOMBRE DEL SITIO"].map(nombre)

    t = pd.crosstab(s["municipio"], s["atender"]).reindex(columns=ATENDER, fill_value=0)
    t["sitios"] = t.sum(axis=1)
    t["atencion"] = t["sitios"] - t["Ninguno recurrente"]
    t = t.sort_values(["atencion", "sitios", "Sales o dureza"], ascending=False)
    t["mun_orden"] = np.arange(1, len(t) + 1)
    t["mun_etiqueta"] = [f"{m} · {int(f.atencion)} de {int(f.sitios)}" for m, f in t.iterrows()]
    s = s.join(t[["mun_orden", "mun_etiqueta"]], on="municipio")
    s["atender_desc"] = s["atender"].map(DESCRIPCION)
    s["clase"] = s["atender"]
    anios = r.assign(a=r["ANIO"].astype(int)).groupby("CLAVE SITIO")["a"].agg(["min", "max"])
    s = s.join(anios, on="CLAVE SITIO")
    s["periodo_texto"] = [f"{int(n)} muestreos de {int(a)} a {int(b)}" if a != b else f"{int(n)} muestreos en {int(a)}"
                          for n, a, b in zip(s["muestreos"], s["min"], s["max"])]
    s["rotulo"] = ""
    for mun in ROTULOS:
        del_mun = s[s["municipio"] == mun].sort_values(["muestreos", "CLAVE SITIO"], ascending=[False, True])
        s.loc[del_mun.index[0], "rotulo"] = mun
    s["con_bac"] = np.where(s["COLI_FEC_n"] > 0, "Con medición", "Sin medición")

    def texto(exc, n, vacio):
        return [f"{int(e)} de {int(k)} muestreos" if k > 0 else vacio for e, k in zip(exc.fillna(0), n.fillna(0))]

    s["sal_texto"] = texto(s["SDT_exc"], s["SDT_n"], "sin medición")
    s["dur_texto"] = texto(s["DUR_TOT_exc"], s["DUR_TOT_n"], "sin medición")
    s["bac_texto"] = texto(s["COLI_FEC_exc"], s["COLI_FEC_n"], "sin medición de coliformes")

    def numero(col):
        v = r[col].astype("string").str.strip()
        return pd.to_numeric(v.str.lstrip("<>"), errors="coerce"), v.str.startswith("<").fillna(False)

    sdt, _ = numero("SDT")
    dur, _ = numero("DUR_TOT")
    col, col_cens = numero("COLI_FEC")
    m = pd.DataFrame({
        "tipo": "muestreo", "clave": r["CLAVE SITIO"], "fecha": pd.to_datetime(r["FECHA"]).dt.date, "anio": r["ANIO"].astype(int),
        "sdt": sdt, "dureza": dur, "coliformes": col,
        "sal_exc": np.where(sdt.isna(), np.nan, (sdt > 1000).astype(float)),
        "dur_exc": np.where(dur.isna(), np.nan, (dur > 500).astype(float)),
        "bac_det": np.where(col.isna(), np.nan, ((col > 0) & ~col_cens).astype(float)),
        "bac_mil": np.where(col.isna(), np.nan, ((col > 1000) & ~col_cens).astype(float)),
        "uno": 1,
    })
    sitio = s.set_index("CLAVE SITIO")
    for destino, origen in [("sitio", "sitio"), ("municipio", "municipio"), ("subtipo", "subtipo"), ("atender", "atender"), ("pos_x", "lon"),
                            ("sitio_x", "lon"), ("pos_y", "lat"), ("muestreos_sitio", "muestreos"), ("anios_sitio", "anios"),
                            ("orden_po", "orden_po"), ("sal_movil", "sal_movil"), ("bac_movil", "bac_movil"), ("mun_etiqueta", "mun_etiqueta"),
                            ("mun_orden", "mun_orden"), ("atender_desc", "atender_desc"), ("con_bac", "con_bac"),
                            ("sal_texto", "sal_texto"), ("dur_texto", "dur_texto"), ("bac_texto", "bac_texto"), ("clase", "clase"), ("rotulo", "rotulo"), ("periodo_texto", "periodo_texto")]:
        m[destino] = m["clave"].map(sitio[origen])
    m["anio_txt"] = m["anio"].astype(str)
    m["atender_x"] = m["atender"].map({c: float(i + 1) for i, c in enumerate(ATENDER)})
    m["orden_inv"] = len(s) + 1 - m["orden_po"]
    est = sa.set_index(["CLAVE SITIO", "ANIO"])
    llave = list(zip(m["clave"], m["anio"]))
    m["estado_sal"] = [{1.0: "Sobre la referencia", 0.0: "Dentro de la referencia"}.get(est.loc[k, "sal"], "Sin medición") for k in llave]
    m["estado_bac"] = [{1.0: "Con coliformes", 0.0: "Sin coliformes"}.get(est.loc[k, "bac"], "Sin medición") for k in llave]

    geo = json.load(open(geojson, encoding="utf-8"))
    yuc = next(f for f in geo["features"] if f["properties"]["name"] == "Yucatán")
    assert yuc["geometry"]["type"] == "Polygon"
    borde = pd.DataFrame(yuc["geometry"]["coordinates"][0], columns=["pos_x", "borde_y"])
    borde["orden_borde"] = np.arange(1, len(borde) + 1)
    borde["poligono"] = "Yucatán"
    borde["tipo"] = "contorno"
    # Fuera del rango de los ejes fijos: así ninguna marca queda con valor vacío (sin aviso de nulos).
    borde["pos_y"] = 0.0
    borde["subtipo"] = "Pozo"
    borde["muestreos_sitio"] = int(s["muestreos"].min())
    m["borde_y"] = 0.0
    m["orden_borde"] = 0
    m["poligono"] = "fuera"
    etiqueta = s.drop_duplicates("municipio").set_index("municipio")
    borde["rotulo"] = ""
    copias = [borde.assign(municipio=mun, atender=cl, clase=cl, atender_desc=DESCRIPCION[cl], mun_etiqueta=etiqueta.loc[mun, "mun_etiqueta"],
                           atender_x=float(ATENDER.index(cl) + 1),
                           mun_orden=int(etiqueta.loc[mun, "mun_orden"]))
              for mun in MUNICIPIOS.values() for cl in ATENDER]
    todo = pd.concat([m] + copias, ignore_index=True)
    todo = todo[[c for c, _ in COLUMNAS]]
    assert (todo["tipo"] == "muestreo").sum() == 683
    assert todo.loc[todo["tipo"] == "muestreo", "clave"].nunique() == 121
    return todo


def a_hyper(df, salida):
    from tableauhyperapi import Connection, CreateMode, HyperProcess, Inserter, SqlType, TableDefinition, TableName, Telemetry
    tipos = {"string": SqlType.text(), "integer": SqlType.big_int(), "date": SqlType.date(), "real": SqlType.double()}
    definicion = TableDefinition(TableName("Extract", "Extract"), [TableDefinition.Column(c, tipos[t]) for c, t in COLUMNAS])
    filas = []
    for rec in df.itertuples(index=False):
        fila = []
        for (c, t), v in zip(COLUMNAS, rec):
            if v is None or pd.isna(v):
                fila.append(None)
            elif t == "integer":
                fila.append(int(v))
            elif t == "real":
                fila.append(float(v))
            elif t == "date":
                fila.append(v)
            else:
                fila.append(str(v))
        filas.append(fila)
    salida.parent.mkdir(parents=True, exist_ok=True)
    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
        with Connection(hp.endpoint, salida, CreateMode.CREATE_AND_REPLACE) as con:
            con.catalog.create_schema("Extract")
            con.catalog.create_table(definicion)
            with Inserter(con, definicion) as ins:
                ins.add_rows(filas)
                ins.execute()
            n = con.execute_scalar_query('SELECT COUNT(*) FROM "Extract"."Extract"')
            sitios = con.execute_scalar_query('SELECT COUNT(DISTINCT "clave") FROM "Extract"."Extract"')
    return n, sitios


if __name__ == "__main__":
    proc, geojson, salida = (sys.argv[1:4] if len(sys.argv) >= 4 else (PROC, GEOJSON, BUILD))
    salida = Path(salida)
    df = tabla(proc, geojson)
    salida.mkdir(parents=True, exist_ok=True)
    df.to_excel(salida / "dos-mapas-datos.xlsx", sheet_name="Datos", index=False)
    (salida / "filas.txt").write_text(str(len(df)), encoding="utf-8")
    try:
        n, sitios = a_hyper(df, salida / "Extract" / "Datos.hyper")
    except ImportError:
        n, sitios = "sin tableauhyperapi", df.loc[df["tipo"] == "muestreo", "clave"].nunique()
    print("filas", len(df), "| hyper", n, "| sitios", sitios, "| contorno", int((df["tipo"] == "contorno").sum()))
    print(df[df["tipo"] == "muestreo"].groupby("atender")["clave"].nunique().to_dict())
