"""Verifica cada cifra del Evidence Board contra el archivo original de CONAGUA.

Cada prueba recalcula la cifra desde Subterraneo.xlsb (sin usar las tablas derivadas) y
comprueba que el texto exacto aparece en el documento fuente del Evidence Board.

Uso: python -m pytest analisis/pruebas/test_evidence.py -q
"""
import re
import unicodedata
from html import unescape
from pathlib import Path

import pandas as pd
import pytest
from scipy.stats import kendalltau

RAIZ = Path(__file__).resolve().parents[2]


def primero(*rutas):
    for r in rutas:
        if r.exists():
            return r
    raise FileNotFoundError(rutas)


ORIGINAL = primero(RAIZ / "datos" / "Subterraneo.xlsb", RAIZ / "datos-crudos" / "renameca" / "Subterraneo.xlsb")
DOC = primero(RAIZ / "documento", RAIZ / "entregas" / "02-evidence-board")
PDF = primero(RAIZ / "sapos-ai-evidence-board.pdf", DOC / "sapos-ai-evidence-board.pdf")

ZONAS = ["Poniente", "Franja de Mérida", "Centro", "Oriente"]
CORTES = [-91, -89.9, -89.3, -88.6, -87]


def plano(t):
    return "".join(c for c in unicodedata.normalize("NFD", str(t)) if unicodedata.category(c) != "Mn").strip().upper()


@pytest.fixture(scope="session")
def datos():
    sitios = pd.read_excel(ORIGINAL, sheet_name="SITIOS", engine="pyxlsb", dtype=object)
    res = pd.read_excel(ORIGINAL, sheet_name="RESULTADOS", engine="pyxlsb", dtype=object)
    sitios.columns = [plano(c) for c in sitios.columns]
    res.columns = [plano(c) if i < 6 else c for i, c in enumerate(res.columns)]
    crudo_municipios = sitios.loc[sitios["ESTADO"].map(plano) == "YUCATAN", "MUNICIPIO"].nunique()
    s = sitios[sitios["ESTADO"].map(plano) == "YUCATAN"].copy()
    s["MUNICIPIO"] = s["MUNICIPIO"].map(plano)
    s["zona"] = pd.cut(s["LONGITUD"].astype(float), CORTES, labels=ZONAS).astype(str)
    s["subtipo"] = s["SUBTIPO CUERPO AGUA"].map(plano)
    r = res[res["CLAVE SITIO"].isin(s["CLAVE SITIO"])].copy()
    r["ANIO"] = r["ANO"].astype(float).astype(int)
    r["FECHA"] = pd.to_datetime(r["FECHA REALIZACION"].astype(float), unit="D", origin="1899-12-30")
    r = r.merge(s[["CLAVE SITIO", "zona", "subtipo"]], on="CLAVE SITIO")
    r["anios"] = r.groupby("CLAVE SITIO")["ANIO"].transform("nunique")
    return s, r, len(sitios), len(res), crudo_municipios


@pytest.fixture(scope="session")
def texto():
    html = (DOC / "evidence-board.html").read_text(encoding="utf-8")
    cuerpo = html.split("</style>")[1]
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", cuerpo)).replace("\xa0", " "))


def dice(texto, frase):
    assert re.sub(r"\s+", " ", frase) in texto, f"El documento no dice: {frase}"


def valores(df, col):
    v = df[col].dropna().astype(str).str.strip()
    v = v[v != ""]
    return v, v.str.startswith("<"), v.str.lstrip("<>").astype(float)


def medir(df, col, limite):
    """(muestreos con dato, muestreos sobre la referencia, porcentaje con un decimal)."""
    v, cens, x = valores(df, col)
    exc = int(((x > limite) & ~cens).sum())
    return len(v), exc, f"{exc / len(v) * 100:.1f}"


def clases(df, col, limite):
    """Sitios por clase: sin medir, nunca, a veces, mayoría (la mitad o más)."""
    v, cens, x = valores(df, col)
    e = ((x > limite) & ~cens).groupby(df.loc[v.index, "CLAVE SITIO"]).agg(["sum", "count"])
    pct = e["sum"] / e["count"]
    total = df["CLAVE SITIO"].nunique()
    return total - len(e), int((e["sum"] == 0).sum()), int(((e["sum"] > 0) & (pct < 0.5)).sum()), int((pct >= 0.5).sum())


# ---------- Hallazgo: sales y dureza por zona ----------

ESPERADO_ZONA = {
    "Poniente": dict(sitios=9, sdt=(30, 26, "86.7"), dur=(29, 26, "89.7"), col=(22, 6, "27.3")),
    "Franja de Mérida": dict(sitios=69, sdt=(465, 133, "28.6"), dur=(438, 152, "34.7"), col=(416, 140, "33.7")),
    "Centro": dict(sitios=30, sdt=(105, 10, "9.5"), dur=(103, 26, "25.2"), col=(83, 27, "32.5")),
    "Oriente": dict(sitios=13, sdt=(81, 12, "14.8"), dur=(77, 14, "18.2"), col=(81, 43, "53.1")),
}


@pytest.mark.parametrize("zona", ZONAS)
def test_cifras_por_zona(datos, zona):
    s, r, *_ = datos
    e = ESPERADO_ZONA[zona]
    rz = r[r["zona"] == zona]
    assert int((s["zona"] == zona).sum()) == e["sitios"]
    assert medir(rz, "SDT", 1000) == e["sdt"]
    assert medir(rz, "DUR_TOT", 500) == e["dur"]
    assert medir(rz, "COLI_FEC", 0) == e["col"]


@pytest.mark.parametrize("figura,clave", [("fig-zona-sales.svg", "sdt"), ("fig-zona-dureza.svg", "dur"), ("fig-zona-bacterias.svg", "col")])
def test_graficas_por_zona_muestran_las_cifras(figura, clave):
    svg = (DOC / figura).read_text(encoding="utf-8")
    for zona in ZONAS:
        n, _, pct = ESPERADO_ZONA[zona][clave]
        assert f">{zona}<" in svg and f">{n} muestreos<" in svg and f">{pct} %<" in svg


def test_texto_del_hallazgo(texto):
    dice(texto, "Supera la referencia de sólidos disueltos 86.7 % de los muestreos del Poniente, 28.6 % de la Franja de Mérida, 9.5 % del Centro y 14.8 % del Oriente.")
    dice(texto, "De 89.7 % en el Poniente a 18.2 % en el Oriente.")
    dice(texto, "En cenotes, 79.4 % de 97 muestreos; en pozos, 27.5 % de 505.")
    dice(texto, "Las sales y la dureza son más frecuentes hacia el poniente del estado; las bacterias fecales aparecen en las cuatro zonas y con mayor frecuencia en los cenotes.")
    dice(texto, "El Poniente son 9 sitios y 30 muestreos.")
    dice(texto, "Tiene sitios en 64 de los 106 municipios del estado y 69 de 121 sitios están en la Franja de Mérida")


def test_tabla_por_zona(datos, texto):
    s, r, *_ = datos
    esperado = {"Poniente": (9, 9, "1,506.5", 5, 2), "Franja de Mérida": (69, 21, "765.0", 48, 31),
                "Centro": (30, 2, "624.5", 22, 11), "Oriente": (13, 2, "765.5", 13, 7)}
    for zona, (n, mayoria, mediana, medidos, detectado) in esperado.items():
        rz = r[r["zona"] == zona]
        assert clases(rz, "SDT", 1000)[3] == mayoria
        v, _, x = valores(rz, "SDT")
        med = x.groupby(rz.loc[v.index, "CLAVE SITIO"]).median().median()
        assert f"{med:,.1f}" == mediana
        sin, nunca, aveces, may = clases(rz, "COLI_FEC", 0)
        assert n - sin == medidos and aveces + may == detectado
        dice(texto, f"{zona} {n} {mayoria} de {n} {mediana} mg/L {medidos} {detectado}")


# ---------- Mapas ----------

def test_clases_de_los_mapas(datos, texto):
    _, r, *_ = datos
    assert clases(r, "SDT", 1000) == (0, 71, 16, 34)
    assert clases(r, "COLI_FEC", 0) == (33, 37, 33, 18)
    dice(texto, "Nunca (71 sitios)")
    dice(texto, "A veces (16)")
    dice(texto, "En la mitad o más de sus muestreos (34)")
    dice(texto, "Nunca (37)")
    dice(texto, "A veces (33)")
    dice(texto, "En la mitad o más (18)")
    dice(texto, "Sin medición (33)")


@pytest.mark.parametrize("figura", ["fig-mapa-sales.svg", "fig-mapa-bacterias.svg"])
def test_mapas_dibujan_121_sitios(figura):
    svg = (DOC / figura).read_text(encoding="utf-8")
    assert svg.count("<circle") == 113 and svg.count('transform="rotate(45') == 8


def test_colores_de_los_mapas_coinciden_con_las_clases():
    sal = (DOC / "fig-mapa-sales.svg").read_text(encoding="utf-8")
    assert (sal.count('fill="#c6dde1"'), sal.count('fill="#4f9aa6"'), sal.count('fill="#0a4a55"')) == (71, 16, 34)
    bac = (DOC / "fig-mapa-bacterias.svg").read_text(encoding="utf-8")
    assert (bac.count('fill="#f0d6c2"'), bac.count('fill="#cf8552"'), bac.count('fill="#8a3a12"')) == (37, 33, 18)


def test_definicion_de_zonas(texto):
    dice(texto, "Poniente (al oeste de 89.9° O; sitios de Celestún, Halachó, Kinchil, Maxcanú, Samahil y Tetiz), Franja de Mérida (89.9° a 89.3° O), Centro (89.3° a 88.6° O) y Oriente (al este de 88.6° O)")


# ---------- Cenotes y pozos ----------

def test_cenotes_y_pozos(datos, texto):
    s, r, *_ = datos
    cen, poz = r[r["subtipo"] == "CENOTE"], r[r["subtipo"] == "POZO"]
    assert medir(cen, "COLI_FEC", 0) == (97, 77, "79.4")
    assert medir(poz, "COLI_FEC", 0) == (505, 139, "27.5")
    assert clases(cen, "COLI_FEC", 0) == (0, 0, 1, 7)
    sin, nunca, aveces, may = clases(poz, "COLI_FEC", 0)
    assert (113 - sin, aveces + may, may) == (80, 43, 11)
    dice(texto, "Los 8 cenotes de la red tuvieron al menos una detección y 7 la tuvieron en la mitad o más de sus muestreos. De 80 pozos con medición, 43 tuvieron alguna detección y 11 en la mitad o más.")
    dice(texto, "(97 muestreos de coliformes en 8 cenotes; 505 en 80 pozos)")
    svg = (DOC / "fig-subtipo-bacterias.svg").read_text(encoding="utf-8")
    assert ">79.4 %<" in svg and ">27.5 %<" in svg and ">97 muestreos<" in svg and ">505 muestreos<" in svg


# ---------- Todos los parámetros ----------

def test_todos_los_parametros(datos):
    _, r, *_ = datos
    esperado = {"COLI_FEC": (0, 602, "35.9"), "DUR_TOT": (500, 647, "33.7"), "SDT": (1000, 681, "26.6"), "AS_TOT": (0.01, 600, "3.0"),
                "N_NO3": (11, 613, "2.9"), "CR_TOT": (0.05, 557, "1.8"), "PB_TOT": (0.01, 538, "0.0"), "HG_TOT": (0.006, 626, "0.0"),
                "CD_TOT": (0.003, 577, "0.0")}
    svg = (DOC / "fig-parametros.svg").read_text(encoding="utf-8")
    for col, (lim, n, pct) in esperado.items():
        m = medir(r, col, lim)
        assert (m[0], m[2]) == (n, pct), col
        assert f">{n} muestreos<" in svg
    assert svg.count(">0.0 %<") == 3


# ---------- En el tiempo ----------

def test_tendencia_de_solidos_disueltos(datos, texto):
    _, r, *_ = datos
    largos = r[r["anios"] >= 8]
    sube = baja = nada = 0
    for _, t in largos.groupby("CLAVE SITIO"):
        v, _, x = valores(t, "SDT")
        a = x.groupby(t.loc[v.index, "ANIO"]).median()
        assert len(a) >= 8
        tau, p = kendalltau(a.index, a.values)
        if p < 0.05 and tau > 0:
            sube += 1
        elif p < 0.05 and tau < 0:
            baja += 1
        else:
            nada += 1
    assert (largos["CLAVE SITIO"].nunique(), sube, baja, nada) == (30, 0, 3, 27)
    dice(texto, "0 de 30 sitios con ocho o más años de datos muestran un aumento significativo de sólidos disueltos. En 3 baja y en 27 no hay tendencia.")


def test_coliformes_en_sitios_largos(datos, texto):
    _, r, *_ = datos
    largos = r[(r["anios"] >= 8) & (r["ANIO"] <= 2020)]
    pct = []
    for _, t in largos.groupby("ANIO"):
        pct.append(float(medir(t, "COLI_FEC", 0)[2]))
    assert len(pct) == 9 and (min(pct), max(pct)) == (13.8, 59.3)
    tardios = r[(r["anios"] >= 8) & r["COLI_FEC"].notna()]
    assert (int((tardios["ANIO"] == 2021).sum()), int((tardios["ANIO"] == 2022).sum())) == (8, 14)
    dice(texto, "(2021 y 2022 tienen menos de 15 muestreos con coliformes)")
    dice(texto, "la detección de coliformes varió entre 13.8 % y 59.3 % de los muestreos por año de 2012 a 2020")


# ---------- Preparación y calidad ----------

def test_recorte_y_calidad(datos, texto):
    s, r, n_sitios, n_res, grafias = datos
    assert (len(s), n_sitios, len(r), n_res) == (121, 2872, 683, 14519)
    assert (grafias, s["MUNICIPIO"].nunique()) == (75, 64)
    assert int(r.duplicated(["CLAVE SITIO", "FECHA"]).sum()) == 0
    assert r["CLAVE SITIO"].nunique() == 121
    assert (r["FECHA"].dt.year == r["ANIO"]).all()
    assert (str(r["FECHA"].min().date()), str(r["FECHA"].max().date())) == ("2012-11-24", "2023-11-15")
    lat, lon = s["LATITUD"].astype(float), s["LONGITUD"].astype(float)
    assert lat.between(19.5, 21.7).all() and lon.between(-90.5, -87.4).all()
    dice(texto, "121 de 2,872 sitios; 683 de 14,519 registros")
    dice(texto, "75 grafías en la fuente; 64 municipios tras unificar")
    dice(texto, "121 sitios y 683 muestreos de Yucatán, del 24 nov 2012 al 15 nov 2023; 9 parámetros")
    dice(texto, "Coinciden en los 683 registros")


def test_valores_bajo_el_limite_de_deteccion(datos, texto):
    _, r, *_ = datos
    esperado = {"COLI_FEC": "64.1", "AS_TOT": "96.5", "CR_TOT": "81.9", "PB_TOT": "98.1", "HG_TOT": "89.9", "CD_TOT": "100.0", "N_NO3": "3.1", "SDT": "0.0", "DUR_TOT": "0.0"}
    for col, pct in esperado.items():
        v, cens, _ = valores(r, col)
        assert f"{cens.mean() * 100:.1f}" == pct, col
    dice(texto, "Coliformes 64.1 %; arsénico 96.5 %; cromo 81.9 %; plomo 98.1 %; mercurio 89.9 %; cadmio 100 %; nitratos 3.1 %; sólidos disueltos y dureza 0 %")
    v, cens, x = valores(r, "COLI_FEC")
    assert (x[cens].min(), x[cens].max()) == (1, 30)


def test_cobertura_de_coliformes_y_cambios_en_la_red(datos, texto):
    _, r, *_ = datos
    assert r.loc[r["COLI_FEC"].notna(), "CLAVE SITIO"].nunique() == 88
    assert r.loc[r["COLI_FEC"].notna(), "ANIO"].max() == 2022
    sit = r.groupby("ANIO")["CLAVE SITIO"].nunique()
    assert (sit[2018], sit[2019]) == (36, 71)
    assert int((r["ANIO"] == 2021).sum()) == 11
    assert r.groupby("CLAVE SITIO")["ANIO"].min().value_counts()[2022] == 33
    con = r[r["COLI_FEC"].notna()]
    assert (int((con["ANIO"] == 2022).sum()), int((r["ANIO"] == 2022).sum())) == (42, 82)
    assert (int((con["ANIO"] == 2023).sum()), int((r["ANIO"] == 2023).sum())) == (0, 40)
    primer = r.groupby("CLAVE SITIO")["ANIO"].min()
    assert set(r["CLAVE SITIO"]) - set(con["CLAVE SITIO"]) == set(primer.index[primer == 2022])
    dice(texto, "33 de 121, que son los 33 sitios incorporados en 2022. Hay coliformes en 42 de 82 muestreos de 2022 y en ninguno de 2023")
    dice(texto, "De 36 a 71 sitios muestreados en 2019; 11 muestreos en 2021; 33 sitios nuevos en 2022")


# ---------- Reglas del concurso ----------

@pytest.mark.parametrize("elemento", ["Datos utilizados", "Preparación y calidad del dato", "Procedimientos", "Resultados por zona", "Hallazgo", "Límites"])
def test_contenido_que_pide_el_readme(texto, elemento):
    assert elemento in texto


def test_observado_interpretacion_implicacion(texto):
    for parte in ("Observado", "Interpretación", "Implicación"):
        assert parte in texto
    dice(texto, "No identificamos el origen de ninguno de los dos.")
    dice(texto, "no afirma causas")


def test_declaracion_e_integrantes(texto):
    dice(texto, "Uso de herramientas.")
    dice(texto, "asistente de IA (Claude, de Anthropic)")
    for nombre in ("Christian Carreño", "Christopher Quiñones", "Daniel Gómez", "Eliana Osorio", "Raúl Cetina"):
        assert nombre in texto


def test_pdf_de_dos_a_tres_paginas():
    crudo = PDF.read_bytes().decode("latin-1")
    assert 2 <= len(re.findall(r"/Type\s*/Page[^s]", crudo)) <= 3


def test_pdf_generado_despues_de_la_fuente():
    if (RAIZ / "datos").exists():
        pytest.skip("solo aplica en la carpeta de trabajo del equipo")
    assert PDF.stat().st_mtime >= (DOC / "evidence-board.html").stat().st_mtime
    for svg in DOC.glob("*.svg"):
        assert PDF.stat().st_mtime >= svg.stat().st_mtime, svg.name


# ---------- Precisiones pedidas por la auditoría independiente ----------

def test_coliformes_solo_en_pozos_por_zona(datos, texto):
    _, r, *_ = datos
    pozos = r[r["subtipo"] == "POZO"]
    esperado = {"Poniente": (11, 2, "18.2"), "Franja de Mérida": (368, 103, "28.0"), "Centro": (68, 13, "19.1"), "Oriente": (58, 21, "36.2")}
    for zona, e in esperado.items():
        assert medir(pozos[pozos["zona"] == zona], "COLI_FEC", 0) == e
    dice(texto, "Solo en pozos, la detección de coliformes por zona es 18.2 % (Poniente, 11 muestreos), 28.0 % (Franja de Mérida, 368), 19.1 % (Centro, 68) y 36.2 % (Oriente, 58).")
    dice(texto, "solo en pozos, de 18.2 % a 36.2 % de los muestreos por zona")


def test_cenotes_del_oriente(datos, texto):
    s, r, *_ = datos
    c = r[(r["subtipo"] == "CENOTE") & (r["zona"] == "Oriente")]
    assert c["CLAVE SITIO"].nunique() == 2
    assert set(s.loc[s["CLAVE SITIO"].isin(c["CLAVE SITIO"]), "MUNICIPIO"]) == {"CHEMAX"}
    assert medir(c, "COLI_FEC", 0)[:2] == (23, 22)
    dice(texto, "El 53.1 % del Oriente incluye dos cenotes de Chemax (22 detecciones en 23 muestreos); solo en pozos es 36.2 %.")


def test_sales_al_oeste_de_merida(datos, texto):
    s, r, *_ = datos
    v, cens, x = valores(r, "SDT")
    e = ((x > 1000) & ~cens).groupby(r.loc[v.index, "CLAVE SITIO"]).mean()
    mitad = set(e.index[e >= 0.5])
    lon = s.set_index("CLAVE SITIO")["LONGITUD"].astype(float)
    assert (len(mitad), int((lon[list(mitad)] < -89.6).sum())) == (34, 25)
    dice(texto, "De los 34 sitios que la superan en la mitad o más de sus muestreos, 25 están al oeste de 89.6° O.")


def test_sitios_con_seguimiento_largo(datos, texto):
    s, r, *_ = datos
    largos = r[r["anios"] >= 8]
    assert largos["CLAVE SITIO"].nunique() == 30
    assert largos.loc[largos["subtipo"] == "CENOTE", "CLAVE SITIO"].nunique() == 5
    assert largos.groupby("CLAVE SITIO")["ANIO"].min().max() <= 2013
    dice(texto, "son de la red original e incluyen 5 cenotes")


def test_referencias_declaradas(texto):
    dice(texto, "Referencias de la NOM-127-SSA1-2021, en mg/L: dureza 500; sólidos disueltos 1,000; nitrógeno de nitratos 11; cromo 0.05; plomo 0.01; mercurio 0.006; arsénico 0.01 y cadmio 0.003 (límites de cumplimiento gradual, tabla 5). Coliformes fecales: cualquier detección")


def test_titulo_y_bajada(texto):
    dice(texto, "Reto Yucatán Vivo: El agua que no vemos")
    dice(texto, "Dos mapas bajo Yucatán")
    dice(texto, "Qué tiene el agua subterránea monitoreada de Yucatán, dónde, y qué tratamiento pide.")


def test_coliformes_sobre_mil(datos, texto):
    _, r, *_ = datos
    n, exc, pct = medir(r, "COLI_FEC", 1000)
    v, cens, x = valores(r, "COLI_FEC")
    sitios = r.loc[v.index[(x > 1000) & ~cens], "CLAVE SITIO"].nunique()
    assert (n, exc, pct, sitios) == (602, 42, "7.0", 19)
    dice(texto, "con el umbral de 1,000 NMP/100 mL, que CONAGUA clasifica como «contaminada», lo superan 7.0 % de los 602 muestreos, en 19 sitios.")


# ---------- Los dos mapas juntos: qué atender en cada sitio ----------

def test_que_atender_en_cada_sitio(datos, texto):
    s, r, *_ = datos

    def mitad(col, limite):
        v, cens, x = valores(r, col)
        e = ((x > limite) & ~cens).groupby(r.loc[v.index, "CLAVE SITIO"]).mean()
        return set(e.index[e >= 0.5])

    sal = mitad("SDT", 1000) | mitad("DUR_TOT", 500)
    bac = mitad("COLI_FEC", 0)
    medidos = set(r.loc[r["COLI_FEC"].notna(), "CLAVE SITIO"])
    info = s.set_index("CLAVE SITIO")

    def clase(k):
        if k in sal and k in bac:
            return "Ambos"
        return "Sales o dureza" if k in sal else "Bacterias" if k in bac else "Ninguno"

    info["clase"] = [clase(k) for k in info.index]
    esperado = {"Poniente": (9, 0, 8, 0, 1), "Franja de Mérida": (69, 24, 33, 9, 3), "Centro": (30, 22, 7, 1, 0), "Oriente": (13, 6, 3, 3, 1)}
    for zona, e in esperado.items():
        z = info[info["zona"] == zona]
        fila = (len(z),) + tuple(int((z["clase"] == c).sum()) for c in ("Ninguno", "Sales o dureza", "Bacterias", "Ambos"))
        assert fila == e, zona
        dice(texto, f"{zona} " + " ".join(str(n) for n in e))
    total = tuple(int((info["clase"] == c).sum()) for c in ("Ninguno", "Sales o dureza", "Bacterias", "Ambos"))
    assert total == (52, 51, 13, 5)
    dice(texto, "Yucatán 121 52 51 13 5")
    sin = info[~info.index.isin(medidos)]
    assert (len(sin), int((sin["clase"] == "Ninguno").sum()), int((sin["clase"] == "Sales o dureza").sum())) == (33, 15, 18)
    dice(texto, "En 33 sitios no se midieron coliformes (15 de «ninguno» y 18 de «sales o dureza»)")
    ambos = info[info["clase"] == "Ambos"]
    assert sorted(zip(ambos["MUNICIPIO"], ambos["subtipo"])) == [("CHAPAB", "CENOTE"), ("CHEMAX", "POZO"), ("HALACHO", "POZO"), ("KOPOMA", "CENOTE"), ("OPICHEN", "POZO")]
    dice(texto, "Los 5 sitios con ambos: un pozo en Chemax, uno en Halachó y uno en Opichén, y dos cenotes, en Chapab y Kopomá.")


def test_municipios_del_poniente(datos):
    s, *_ = datos
    assert sorted(s.loc[s["zona"] == "Poniente", "MUNICIPIO"].unique()) == ["CELESTUN", "HALACHO", "KINCHIL", "MAXCANU", "SAMAHIL", "TETIZ"]


def test_semaforo_de_conagua_explicado(texto):
    dice(texto, "CONAGUA publica un semáforo que resume cada sitio en un solo valor del periodo (mediana, promedio o media geométrica, según el parámetro).")
    dice(texto, "indicadores sanitarios (rojo) y de salinidad y dureza (amarillo)")


# ---------- Lo que un resumen por sitio no deja ver ----------

def test_resumen_por_sitio_frente_a_muestreos(datos, texto):
    import numpy as np
    _, r, *_ = datos
    v, cens, x = valores(r, "COLI_FEC")
    sitio = r.loc[v.index, "CLAVE SITIO"]
    media_geo = np.log(x.clip(lower=1)).groupby(sitio).mean().map(np.exp)
    alguna = ((x > 1000) & ~cens).groupby(sitio).any()
    assert (len(media_geo), int((media_geo > 1000).sum()), int(alguna.sum())) == (88, 0, 19)
    v, cens, x = valores(r, "N_NO3")
    sitio = r.loc[v.index, "CLAVE SITIO"]
    mediana = x.groupby(sitio).median()
    alguna = ((x > 11) & ~cens).groupby(sitio).any()
    assert (len(mediana), int((mediana > 11).sum()), int(alguna.sum())) == (121, 3, 14)
    dice(texto, "0 sitios → 19 sitios")
    dice(texto, "ninguno de los 88 sitios medidos lo supera. Muestreo por muestreo, 19 sitios lo superaron al menos una vez, en eventos repartidos entre 2012 y 2022.")
    dice(texto, "3 sitios → 14 sitios")
    dice(texto, "lo superan 3 de 121 sitios. Muestreo por muestreo, 14 sitios lo superaron al menos una vez; 11 de ellos solo en 2021 o 2022, y 10 de esos eventos son de una misma campaña (25 jul a 11 ago de 2022).")
    dice(texto, "no es el semáforo oficial")


def test_nitratos_concentrados_en_una_campana(datos):
    _, r, *_ = datos
    v, cens, x = valores(r, "N_NO3")
    e = r.loc[v.index[(x > 11) & ~cens]]
    assert (len(e), e["CLAVE SITIO"].nunique()) == (18, 14)
    solo_tarde = e.groupby("CLAVE SITIO")["ANIO"].apply(lambda s: set(s) <= {2021, 2022})
    assert int(solo_tarde.sum()) == 11
    campana = e[(e["FECHA"] >= "2022-07-25") & (e["FECHA"] <= "2022-08-11")]
    assert len(campana) == 10


def test_coliformes_sobre_mil_repartidos_en_el_tiempo(datos):
    _, r, *_ = datos
    v, cens, x = valores(r, "COLI_FEC")
    anios = r.loc[v.index[(x > 1000) & ~cens], "ANIO"]
    assert (anios.min(), anios.max(), anios.nunique()) == (2012, 2022, 8)
