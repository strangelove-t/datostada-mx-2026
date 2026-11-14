"""Verifica el tablero de Tableau: cada cifra que muestra se recalcula desde los muestreos de CONAGUA.

Las pruebas leen el libro empaquetado (.twbx), su tabla incorporada y sus textos, y los comparan con
cifras recalculadas aquí mismo a partir de las tablas de Yucatán extraídas del archivo original.

Uso: python -m pytest analisis/pruebas/test_tablero.py -q
"""
import json
import re
import unicodedata
import zipfile
from html import unescape
from io import BytesIO
from pathlib import Path
from xml.dom import minidom

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[2]
NOMBRE = "sapos-ai-dos-mapas-bajo-yucatan"
ATENDER = ["Sales o dureza", "Bacterias", "Ambos", "Ninguno recurrente"]


def primero(*rutas):
    for r in rutas:
        if r.exists():
            return r
    raise FileNotFoundError(rutas)


DER = primero(RAIZ / "datos" / "derivados", RAIZ / "datos-procesados")
ENTREGA = primero(RAIZ / f"{NOMBRE}.twbx", RAIZ / "entregas" / "03-dashboard" / f"{NOMBRE}.twbx").parent
TWBX = ENTREGA / f"{NOMBRE}.twbx"
PDF = ENTREGA / f"{NOMBRE}-respaldo.pdf"


def bandera(serie, limite):
    """Valor numérico y excedencia: «<» es no detectado y nunca excedencia; vacío es sin medición."""
    v = serie.astype("string").str.strip()
    x = pd.to_numeric(v.str.lstrip("<>"), errors="coerce")
    e = ((x > limite) & ~v.str.startswith("<").fillna(False)).astype(float)
    e[x.isna()] = np.nan
    return x, e


def rangos(a, b):
    ok = a.notna() & b.notna()
    return round(float(a[ok].rank().corr(b[ok].rank())), 2), int(ok.sum())


@pytest.fixture(scope="session")
def fuente():
    res = pd.read_csv(DER / "resultados_yucatan.csv", dtype=str, low_memory=False)
    sit = pd.read_csv(DER / "sitios_yucatan.csv", dtype=str)
    res["ANIO"] = res["ANIO"].astype(int)
    res["sdt"], res["sal"] = bandera(res["SDT"], 1000)
    res["dureza"], res["dur"] = bandera(res["DUR_TOT"], 500)
    res["coli"], res["bac"] = bandera(res["COLI_FEC"], 0)
    g = res.groupby("CLAVE SITIO")
    s = sit.set_index("CLAVE SITIO")
    # Un pozo del sistema de agua potable de Peto viene asignado a Mérida en la fuente; el tablero lo cuenta en Peto.
    assert "PETO" in s.loc["OCPYU5381", "NOMBRE DEL SITIO"] and s.loc["OCPYU5381", "MUNICIPIO"] == "MERIDA"
    assert abs(float(s.loc["OCPYU5381", "LATITUD"]) - 20.126) < 0.01 and abs(float(s.loc["OCPYU5381", "LONGITUD"]) + 88.921) < 0.01
    s.loc["OCPYU5381", "MUNICIPIO"] = "PETO"
    s["lon"], s["lat"] = s["LONGITUD"].astype(float), s["LATITUD"].astype(float)
    s["muestreos"] = g.size()
    for c in ("sal", "dur", "bac"):
        s[c + "_n"], s[c + "_exc"] = g[c].count(), g[c].sum()
        s[c + "_pct"] = (s[c + "_exc"] / s[c + "_n"] * 100).round(1)
        s[c + "_rec"] = (s[c + "_n"] > 0) & (s[c + "_pct"] >= 50)
    sales, bacterias = s["sal_rec"] | s["dur_rec"], s["bac_rec"]
    s["atender"] = np.select([sales & bacterias, sales, bacterias], ["Ambos", "Sales o dureza", "Bacterias"], "Ninguno recurrente")
    return res, s


@pytest.fixture(scope="session")
def paquete():
    with zipfile.ZipFile(TWBX) as z:
        nombres = z.namelist()
        twb = z.read(f"{NOMBRE}.twb").decode("utf-8")
        tabla = pd.read_excel(BytesIO(z.read("Data/dos-mapas-datos.xlsx")), sheet_name="Datos")
        hyper = z.read("Data/Extract/Datos.hyper")
    return nombres, twb, tabla, hyper


@pytest.fixture(scope="session")
def texto(paquete):
    return unescape(paquete[1])


@pytest.fixture(scope="session")
def muestreos(paquete):
    return paquete[2][paquete[2]["tipo"] == "muestreo"].copy()


def por_sitio(muestreos, columna):
    return muestreos.groupby("clave")[columna].first()


# ---- 1. El paquete -------------------------------------------------------------------------------
def test_paquete_con_datos_incorporados(paquete):
    nombres, twb, _, hyper = paquete
    assert sorted(nombres) == sorted([f"{NOMBRE}.twb", "Data/dos-mapas-datos.xlsx", "Data/Extract/Datos.hyper"])
    minidom.parseString(twb.encode("utf-8"))
    assert len(hyper) > 50_000
    assert "C:\\" not in twb and "/Users/" not in twb, "el libro no debe apuntar a rutas de una máquina"


def test_dos_vistas_de_tamano_fijo(paquete):
    doc = minidom.parseString(paquete[1].encode("utf-8"))
    tableros = doc.getElementsByTagName("dashboard")
    assert [d.getAttribute("name") for d in tableros] == ["Dos mapas bajo Yucatán", "Cuándo"]
    for d in tableros:
        t = d.getElementsByTagName("size")[0]
        assert (t.getAttribute("maxwidth"), t.getAttribute("maxheight"), t.getAttribute("sizing-mode")) == ("1366", "768", "fixed")
    hojas = {w.getAttribute("name") for w in doc.getElementsByTagName("worksheet")}
    usadas = {z.getAttribute("name") for d in tableros for z in d.getElementsByTagName("zone") if z.getAttribute("name")}
    assert usadas == hojas == {"Mapa", "Cifras", "Perfil sales", "Perfil bacterias", "Municipios", "Franjas sales", "Franjas bacterias"}


def test_interacciones(paquete):
    doc = minidom.parseString(paquete[1].encode("utf-8"))
    acciones = [(a.getElementsByTagName("command")[0].getAttribute("command"), a.getElementsByTagName("source")[0].getAttribute("dashboard"),
                 a.getElementsByTagName("source")[0].getAttribute("worksheet")) for a in doc.getElementsByTagName("action")]
    assert ("tsc:tsl-filter", "Dos mapas bajo Yucatán", "Cifras") in acciones
    assert ("tsc:tsl-filter", "Dos mapas bajo Yucatán", "Municipios") in acciones
    assert ("tsc:brush", "Dos mapas bajo Yucatán", "Mapa") in acciones
    assert ("tsc:brush", "Cuándo", "") in acciones


def test_extracto_con_las_mismas_filas(paquete, tmp_path):
    api = pytest.importorskip("tableauhyperapi")
    ruta = tmp_path / "Datos.hyper"
    ruta.write_bytes(paquete[3])
    with api.HyperProcess(telemetry=api.Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
        with api.Connection(hp.endpoint, ruta) as con:
            n = con.execute_scalar_query('SELECT COUNT(*) FROM "Extract"."Extract"')
            m = con.execute_scalar_query('SELECT COUNT(*) FROM "Extract"."Extract" WHERE "tipo" = \'muestreo\'')
    assert (n, m) == (len(paquete[2]), 683)


# ---- 2. La tabla incorporada contra los muestreos -------------------------------------------------
def test_tabla_tiene_todos_los_muestreos(fuente, muestreos):
    res, s = fuente
    assert len(res) == len(muestreos) == 683
    assert set(muestreos["clave"]) == set(s.index) and len(s) == 121
    assert muestreos.groupby("clave").size().sort_index().tolist() == s["muestreos"].sort_index().tolist()


def test_excedencias_por_muestreo(fuente, muestreos):
    res, _ = fuente
    for mia, suya in (("sal", "sal_exc"), ("dur", "dur_exc"), ("bac", "bac_det")):
        assert (int(res[mia].count()), int(res[mia].sum())) == (int(muestreos[suya].count()), int(muestreos[suya].sum())), mia
        por_clave = muestreos.groupby("clave")[suya].sum().sort_index()
        assert por_clave.tolist() == res.groupby("CLAVE SITIO")[mia].sum().sort_index().tolist(), mia
    assert (int(res["sal"].sum()), int(res["sal"].count())) == (181, 681)
    assert (int(res["dur"].sum()), int(res["dur"].count())) == (218, 647)
    assert (int(res["bac"].sum()), int(res["bac"].count())) == (216, 602)


def test_que_atender_en_cada_sitio(fuente, muestreos, texto):
    _, s = fuente
    assert por_sitio(muestreos, "atender").sort_index().tolist() == s["atender"].sort_index().tolist()
    assert s["atender"].value_counts().to_dict() == {"Ninguno recurrente": 52, "Sales o dureza": 51, "Bacterias": 13, "Ambos": 5}
    assert "«Recurrente»: en la mitad o más de los muestreos del sitio" in texto


def test_fichas_por_sitio(fuente, muestreos):
    _, s = fuente
    for c, col, vacio in (("sal", "sal_texto", "sin medición"), ("dur", "dur_texto", "sin medición"), ("bac", "bac_texto", "sin medición de coliformes")):
        esperado = [f"{int(e)} de {int(n)} muestreos" if n > 0 else vacio for e, n in zip(s[c + "_exc"].fillna(0), s[c + "_n"])]
        assert por_sitio(muestreos, col).reindex(s.index).tolist() == esperado, col
    assert por_sitio(muestreos, "subtipo").value_counts().to_dict() == {"Pozo": 113, "Cenote": 8}
    res = fuente[0]
    anios = res.groupby("CLAVE SITIO")["ANIO"].agg(["min", "max", "size"]).reindex(s.index)
    esperado = [f"{n} muestreos de {a} a {b}" if a != b else f"{n} muestreos en {a}" for a, b, n in anios.itertuples(index=False)]
    assert por_sitio(muestreos, "periodo_texto").reindex(s.index).tolist() == esperado


def test_anio_con_pocos_muestreos(fuente, texto):
    assert int((fuente[0]["ANIO"] == 2021).sum()) == 11
    assert "en 2021 solo hubo 11 muestreos" in texto


def test_posicion_de_cada_sitio(fuente, muestreos):
    _, s = fuente
    assert np.allclose(por_sitio(muestreos, "pos_x").reindex(s.index), s["lon"]) and np.allclose(por_sitio(muestreos, "pos_y").reindex(s.index), s["lat"])
    assert s["lon"].between(-90.55, -87.45).all() and s["lat"].between(19.45, 21.72).all(), "todos los sitios caben en los ejes fijos"


def test_contorno_sobrevive_a_los_filtros(paquete, muestreos):
    contorno = paquete[2][paquete[2]["tipo"] == "contorno"]
    vertices = contorno["orden_borde"].nunique()
    assert vertices > 150
    combos = contorno.groupby(["municipio", "atender"]).size()
    assert len(combos) == muestreos["municipio"].nunique() * 4 == 260 and (combos == vertices).all()
    assert (contorno["pos_y"] == 0).all() and (muestreos["borde_y"] == 0).all(), "lo que no toca a cada capa queda fuera del eje, no vacío"


# ---- 3. Perfil de poniente a oriente --------------------------------------------------------------
def test_correlaciones_del_perfil(fuente, texto):
    _, s = fuente
    assert rangos(s["lon"], s["sal_pct"]) == (-0.54, 121)
    con = s[s["bac_n"] > 0]
    assert rangos(con["lon"], con["bac_pct"]) == (-0.02, 88)
    assert rangos(con["lat"], con["bac_pct"]) == (0.03, 88)
    assert "Correlación de Spearman con la longitud: −0.54 (121 sitios)" in texto
    assert "Correlación con la longitud: −0.02; con la latitud: 0.03 (88 sitios)" in texto


def test_cenotes_y_pozos(fuente, texto):
    res, s = fuente
    por_tipo = res.join(s["SUBTIPO CUERPO AGUA"], on="CLAVE SITIO").groupby("SUBTIPO CUERPO AGUA")["bac"].agg(["count", "sum"])
    assert por_tipo.loc["CENOTE"].tolist() == [97, 77] and por_tipo.loc["POZO"].tolist() == [505, 139]
    assert (round(77 / 97 * 100, 1), round(139 / 505 * 100, 1)) == (79.4, 27.5)
    assert "En cenotes, 79.4 % de 97 muestreos; en pozos, 27.5 % de 505" in texto


def test_linea_de_los_perfiles(fuente, muestreos, texto):
    assert "promedio de los 17 sitios vecinos" in texto
    _, s = fuente
    o = s.sort_values("lon", kind="stable")
    sal = (o["sal_pct"] / 100).rolling(17, center=True, min_periods=8).mean()
    con = o[o["bac_n"] > 0]
    bac = (con["bac_pct"] / 100).rolling(17, center=True, min_periods=8).mean()
    assert np.allclose(por_sitio(muestreos, "sal_movil").reindex(sal.index), sal)
    assert np.allclose(por_sitio(muestreos, "bac_movil").reindex(bac.index), bac)



# ---- 4. Cuándo: estabilidad año por año -----------------------------------------------------------
def estados(res, col, minimo_de_anios=1):
    por_anio = res.groupby(["CLAVE SITIO", "ANIO"])[col].max().dropna()
    extremos = por_anio.groupby("CLAVE SITIO").agg(["min", "max", "count"])
    extremos = extremos[extremos["count"] >= minimo_de_anios]
    siempre = int(((extremos["min"] == 1) & (extremos["max"] == 1)).sum())
    nunca = int(((extremos["min"] == 0) & (extremos["max"] == 0)).sum())
    return len(extremos), siempre, nunca, len(extremos) - siempre - nunca


def test_las_sales_se_quedan(fuente, texto):
    assert estados(fuente[0], "sal") == (121, 23, 71, 27)
    assert "94 de 121" in texto
    assert "sitios mantienen su estado de sólidos disueltos todos los años en que se midieron: 23 siempre sobre la referencia y 71 nunca. 27 cambian." in texto


def test_las_bacterias_van_y_vienen(fuente, texto):
    assert estados(fuente[0], "bac") == (88, 3, 37, 48)
    assert "48 de 88" in texto
    assert "sitios con medición de coliformes fecales cambian de un año a otro. 3 los tienen todos los años y 37 nunca." in texto


def test_sitios_con_ocho_anios_o_mas(fuente, texto):
    res = fuente[0]
    sal, bac = estados(res, "sal", 8), estados(res, "bac", 8)
    assert (sal[0], sal[1] + sal[2], bac[0], bac[1] + bac[2]) == (30, 15, 30, 2)
    assert "En los 30 sitios con 8 años o más de datos: 15 mantienen su estado de sólidos disueltos; 2, el de bacterias." in texto


def test_limite_de_deteccion_y_un_solo_muestreo(fuente, texto):
    res = fuente[0]
    v = res["COLI_FEC"].astype("string").str.strip()
    limites = sorted(set(v[v.str.startswith("<").fillna(False)]), key=lambda t: float(t[1:]))
    assert (limites[0], limites[-1]) == ("<1", "<30")
    res = res.assign(bac30=((res["coli"] >= 30) & ~v.str.startswith("<").fillna(False)).astype(float).where(res["coli"].notna()))
    assert estados(res, "bac30")[::3] == (88, 37)
    por_anio = res.groupby(["CLAVE SITIO", "ANIO"]).size()
    assert (int((por_anio == 1).sum()), len(por_anio)) == (432, 523)
    assert "de <1 a <30 NMP/100 mL): con un umbral común de 30, cambian 37 de 88 sitios. En 432 de 523 casos, el estado del año sale de un solo muestreo." in texto
    con_coliformes = pd.to_datetime(res.loc[res["coli"].notna(), "FECHA"])
    assert con_coliformes.max().strftime("%Y-%m") == "2022-10" and "coliformes fecales medidos hasta oct 2022" in texto


def test_franjas_por_sitio_y_anio(fuente, muestreos):
    res, _ = fuente
    for col, campo, si, no in (("sal", "estado_sal", "Sobre la referencia", "Dentro de la referencia"), ("bac", "estado_bac", "Con coliformes", "Sin coliformes")):
        esperado = res.groupby(["CLAVE SITIO", "ANIO"])[col].max().map({1.0: si, 0.0: no}).fillna("Sin medición")
        visto = muestreos.groupby(["clave", "anio"])[campo].agg(lambda x: x.unique().tolist())
        assert all(len(v) == 1 for v in visto), campo
        assert visto.map(lambda v: v[0]).tolist() == esperado.tolist(), campo
    orden = muestreos.groupby("clave")[["orden_po", "pos_x"]].first().sort_values("orden_po")
    assert orden["pos_x"].is_monotonic_increasing and orden["orden_po"].tolist() == list(range(1, 122))


def test_lo_que_un_resumen_por_sitio_no_deja_ver(fuente, texto):
    res, _ = fuente
    v = res["COLI_FEC"].astype("string").str.strip()
    medidos = res.dropna(subset=["coli"])
    media_geometrica = medidos.groupby("CLAVE SITIO")["coli"].apply(lambda x: float(np.exp(np.log(x.clip(lower=1)).mean())))
    sobre_mil = ((res["coli"] > 1000) & ~v.str.startswith("<").fillna(False)).groupby(res["CLAVE SITIO"]).sum()
    assert (len(media_geometrica), int((media_geometrica > 1000).sum()), int((sobre_mil > 0).sum())) == (88, 0, 19)
    assert "0 de 88 sitios con la media geométrica del sitio; 19 sitios con al menos un muestreo" in texto


# ---- 5. Dónde atender primero ---------------------------------------------------------------------
def test_lista_por_municipio(fuente, muestreos):
    _, s = fuente
    t = pd.crosstab(s["MUNICIPIO"], s["atender"])
    total, atencion = t.sum(axis=1), t.sum(axis=1) - t["Ninguno recurrente"]
    assert (len(t), int((atencion > 0).sum())) == (65, 41)
    etiquetas = muestreos.groupby("clave")[["municipio", "mun_etiqueta", "mun_orden"]].first().drop_duplicates().sort_values("mun_orden")
    assert etiquetas["mun_etiqueta"].tolist()[:7] == ["Mérida · 13 de 19", "Chemax · 4 de 4", "Cuzamá · 3 de 4", "Abalá · 3 de 3",
                                                       "Maxcanú · 3 de 3", "Progreso · 3 de 3", "Tixkokob · 3 de 3"]
    for clave, f in muestreos.groupby("clave")[["municipio", "mun_etiqueta"]].first().iterrows():
        m = s.loc[clave, "MUNICIPIO"]
        assert plano(f["municipio"]) == {"OXKUZTCAB": "OXKUTZCAB"}.get(m, m), "solo cambian los acentos y una errata de captura"
        assert f["mun_etiqueta"] == f"{f['municipio']} · {int(atencion[m])} de {int(total[m])}"
    assert etiquetas["mun_orden"].tolist() == list(range(1, 66))
    assert muestreos.loc[muestreos["clave"] == "OCPYU5381", "mun_etiqueta"].iloc[0] == "Peto · 1 de 1"


def plano(x):
    return "".join(c for c in unicodedata.normalize("NFD", x) if unicodedata.category(c) != "Mn").upper()


# ---- 6. Contexto visible: fuente, periodo, unidades y límites ---------------------------------------
def test_pie_con_fuente_periodo_y_limites(fuente, texto):
    res, s = fuente
    fechas = pd.to_datetime(res["FECHA"])
    assert (fechas.min().strftime("%Y-%m-%d"), fechas.max().strftime("%Y-%m-%d")) == ("2012-11-24", "2023-11-15")
    assert (int((s["bac_n"] == 0).sum()), s["MUNICIPIO"].nunique(), int(s["muestreos"].min()), int(s["muestreos"].max())) == (33, 65, 2, 28)
    assert s.loc[s["bac_n"] == 0, "atender"].value_counts().to_dict() == {"Sales o dureza": 18, "Ninguno recurrente": 15}
    assert int((s["muestreos"] == 2).sum()) == 56
    for frase in ("CONAGUA, Red Nacional de Medición de Calidad del Agua (RENAMECA), agua subterránea",
                  "121 sitios (113 pozos y 8 cenotes) en 65 de 106 municipios, 683 muestreos del 24 nov 2012 al 15 nov 2023",
                  "NOM-127-SSA1-2021: sólidos disueltos totales 1,000 mg/L, dureza total 500 mg/L (como CaCO₃), coliformes fecales en cualquier detección",
                  "es agua del acuífero sin tratar, no la que sale de la llave", "56 sitios tienen solo 2 muestreos",
                  "33 sitios no tienen medición de coliformes fecales (18 están en «Sales o dureza» y 15 en «Ninguno recurrente»)",
                  "Un sitio que la fuente asigna a Mérida se cuenta en Peto", "Contorno aproximado del estado: Natural Earth",
                  "El tablero describe; no explica causas",
                  "número de muestreos del sitio (de 2 a 28)", "1,000 NMP/100 mL"):
        assert frase in texto, frase


def test_titulares_que_los_datos_sostienen(texto):
    assert "Las sales son más frecuentes hacia el poniente. Las bacterias no siguen ese mapa." in texto
    assert "Las sales cambian poco de un año a otro. Las bacterias, más." in texto
    for exceso in ("ningún mapa", "se quedan", "dependen del lugar", "en todos los sitios", "Dónde atender primero"):
        assert exceso not in texto, exceso
    for rotulo in (">Lo observado<", ">Interpretación<", ">Implicación<", "Implicación: cada problema pide su tratamiento."):
        assert rotulo in texto, rotulo


def test_sin_alarma_ni_adornos(texto):
    visibles = " ".join(re.findall(r"<run[^>]*>([^<]*)</run>", texto)).lower()
    for palabra in ("peligro", "alerta", "contaminad", "veneno", "tóxic", "el agua que tomas", "crisis"):
        assert palabra not in visibles, palabra
    assert not re.search("[\U0001F300-\U0001FAFF\u2600-\u27BF]", visibles), "sin emojis ni símbolos decorativos"
    assert "gradient" not in texto.lower()


def test_colores_con_un_solo_significado(texto):
    for clase, color in (("Sales o dureza", "#1380a0"), ("Bacterias", "#c2571a"), ("Ambos", "#7d2f63"), ("Ninguno recurrente", "#84909a")):
        assert re.search(rf"<map to=.{color}.><bucket>.{clase}.</bucket></map>", texto), clase


# ---- 7. Respaldo ----------------------------------------------------------------------------------
def test_pdf_de_respaldo():
    pypdf = pytest.importorskip("pypdf")
    lector = pypdf.PdfReader(str(PDF))
    assert len(lector.pages) == 3
    ancho, alto = float(lector.pages[0].mediabox.width), float(lector.pages[0].mediabox.height)
    assert ancho > alto, "páginas horizontales"
    assert "Dos mapas bajo Yucatán" in lector.pages[0].extract_text()


def test_cifras_guardadas_coinciden(fuente):
    cifras = json.loads((DER / "cifras_tablero.json").read_text(encoding="utf-8"))
    assert (cifras["estabilidad"]["sales"]["mantienen"], cifras["estabilidad"]["bacterias"]["cambian"]) == (94, 48)
    assert (cifras["perfil"]["sales_longitud"]["rho"], cifras["perfil"]["bacterias_longitud"]["rho"], cifras["perfil"]["bacterias_latitud"]["rho"]) == (-0.54, -0.02, 0.03)
    assert cifras["sensibilidad_cortes"][0]["poniente_pct"] > cifras["sensibilidad_cortes"][0]["oriente_pct"]
    assert all(c["poniente_pct"] > c["oriente_pct"] for c in cifras["sensibilidad_cortes"])
