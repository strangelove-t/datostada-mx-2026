from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import pandas as pd, glob, sys
from pathlib import Path
B = Path(sys.argv[1]); out = sys.argv[2]
for nm, f in [("Sans", "LiberationSans-Regular.ttf"), ("SansB", "LiberationSans-Bold.ttf")]:
    pdfmetrics.registerFont(TTFont(nm, glob.glob(f"/usr/share/fonts/**/{f}", recursive=True)[0]))
from reportlab.lib.fonts import addMapping
addMapping("Sans", 0, 0, "Sans"); addMapping("Sans", 1, 0, "SansB")
TEAL = colors.HexColor("#0F5E6E"); INK = colors.HexColor("#1F2933"); GRAY = colors.HexColor("#5B6770"); LIGHT = colors.HexColor("#E8F1F3")
body = ParagraphStyle("b", fontName="Sans", fontSize=8.2, leading=10.4, textColor=INK, spaceAfter=3)
small = ParagraphStyle("s", parent=body, fontSize=7.4, leading=9.2, textColor=GRAY)
h = ParagraphStyle("h", fontName="SansB", fontSize=10.5, leading=13, textColor=TEAL, spaceBefore=6, spaceAfter=3, keepWithNext=1)
title = ParagraphStyle("t", fontName="SansB", fontSize=15, leading=18, textColor=INK, spaceAfter=3)
lab = ParagraphStyle("l", fontName="SansB", fontSize=7.5, textColor=GRAY, spaceAfter=2)
box = ParagraphStyle("box", parent=body, fontSize=9, leading=12, backColor=LIGHT, borderPadding=(5, 6, 5, 6), borderColor=TEAL, borderWidth=0, spaceBefore=4, spaceAfter=8)
bl = lambda t: Paragraph("•&nbsp;&nbsp;" + t, ParagraphStyle("bl", parent=body, leftIndent=9, firstLineIndent=-9))
P = lambda t, s=body: Paragraph(t, s)
cellst = ParagraphStyle("c", parent=body, fontSize=7.4, leading=9, spaceAfter=0)
cellh = ParagraphStyle("ch", parent=cellst, fontName="SansB", textColor=colors.white)
def tbl(rows, widths, hdr=True):
    data = [[Paragraph(str(c), cellh if (hdr and i == 0) else cellst) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if hdr else 0)
    st = [("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#C9D6DA")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    if hdr: st.append(("BACKGROUND", (0, 0), (-1, 0), TEAL))
    t.setStyle(TableStyle(st)); return t
W = letter[0] - 1.2 * inch
D = B / "datos"; F = B / "figs"
cob = pd.read_csv(D / "resumen_cobertura.csv"); ind = pd.read_csv(D / "resumen_indicadores.csv")
sub = pd.read_csv(D / "resumen_pozo_vs_cenote.csv"); sem = pd.read_csv(D / "resumen_semaforo.csv", index_col=0)
top = pd.read_csv(D / "resumen_sitios_prioritarios.csv", keep_default_na=False)
s = []
s += [P("DATOSTADA MX 2026 · ENTREGA 2 · EXPLORE · EVIDENCE BOARD", lab),
      P("El agua que no vemos: lo que dicen (y lo que no) los datos oficiales del agua subterránea de Yucatán", title),
      P("<b>Reto:</b> Yucatán Vivo · El agua que no vemos &nbsp;&nbsp;&nbsp; <b>Equipo:</b> Los Ternurines &nbsp;&nbsp;&nbsp; <b>Fecha:</b> 13 de noviembre de 2026", small),
      P("<b>Integrantes:</b> Acosta Kevin, Damaris Ramirez, Esteban Priego, Jose Samos, Arturo Suarez", small), Spacer(1, 5)]
s.append(P("<b>Hallazgo principal.</b> En los 121 sitios que CONAGUA monitorea en Yucatán, casi ningún sitio rebasa los límites de riesgo en el valor del periodo 2012–2025: solo 3 pozos superan 11 mg/L de nitrógeno de nitratos (Halachó, Motul y Tepakán) y ninguno supera 1,000 NMP/100 mL de coliformes fecales. Sin embargo, 4 de cada 10 sitios (48) tienen nitratos por encima de 5 mg/L, los coliformes fecales se concentran en los cenotes (mediana 256 contra 2 en pozos) y la red tiene huecos: 33 sitios no tienen dato de coliformes y el archivo anual 2025 no incluye ningún sitio de Yucatán.", box))
s.append(P("1. Datos usados", h))
s.append(P("<b>Fuente:</b> CONAGUA, Red Nacional de Medición de Calidad del Agua (RENAMECA), «Calidad del Agua Subterránea», archivo <i>Calidad_del_Agua_Subterr_nea_p_2012-2025.xlsx</i> (hoja «CASUB 12-2025», 2,875 sitios nacionales) y archivo anual <i>Calidad_del_Agua_Subterr_nea_a_2025.xlsx</i> (608 sitios), descargados el 13 nov 2026 de gob.mx/conagua/es/articulos/indicadores-de-calidad-del-agua. Umbrales: escalas de CONAGUA incluidas en el mismo archivo (hoja «Escalas Subterráneas») y NOM-127-SSA1-2021."))
s.append(P("<b>Ajuste respecto al Data Brief.</b> El archivo vigente reporta <b>un valor por sitio para todo el periodo 2012–2025</b> (columna PERIODO = «2012-2025»), no registros por fecha de muestreo. Por eso la unidad de análisis es el <b>sitio</b> y no es posible medir tendencias anuales ni recurrencia por sitio con esta fuente; en su lugar se evalúan el nivel del periodo, el tipo de sitio y los huecos de cobertura. La pregunta se mantiene en el mismo reto: <i>¿qué sitios de Yucatán rebasan o se acercan a los límites de nitratos y coliformes fecales, dónde están y qué tan completa es la evidencia?</i>"))
s.append(P("2. Preparación y calidad de los datos", h))
s.append(bl("Se filtró ESTADO = YUCATÁN (121 sitios, todos del acuífero Península de Yucatán) y se conservaron 15 columnas: clave, sitio, municipio, subtipo, coordenadas, conductividad, SDT, coliformes fecales, nitrógeno de nitratos, sus clasificaciones, semáforo y contaminantes."))
s.append(bl("<b>Verificación del extracto:</b> número de sitios y sumas de N-NO₃ (540.25), conductividad (179,057) y SDT (111,681) coinciden con lo calculado sobre el archivo original; el script lo comprueba al correr."))
s.append(bl("Valores «&lt;1» de coliformes se tratan como <b>no detectados</b> (no como cero ni como faltantes); en gráficas se ubican en 0.5. Celdas vacías se tratan como <b>sin dato</b>."))
s.append(bl("Se normalizaron nombres de municipio (acentos, espacios, puntos): 75 variantes → 64 municipios. Se corrigió «OXKUZTCAB» → Oxkutzcab y se marcó el pozo de Peto registrado con municipio Mérida (coordenadas de Peto)."))
cv = cob.values.tolist(); half = (len(cv) + 1) // 2; left, right = cv[:half], cv[half:] + [["", ""]] * (2 * half - len(cv))
s.append(tbl([["Cobertura", "Valor", "Cobertura", "Valor"]] + [l + r for l, r in zip(left, right)], [W * .38, W * .1, W * .42, W * .1]))
s.append(P("3. Procedimientos", h))
s.append(P("(1) Extracción del Excel oficial con JavaScript en el navegador (lectura directa del XLSX, sin modificar valores) → (2) verificación por sumas de control → (3) limpieza y variables derivadas en Python/pandas (incumple N-NO₃ &gt; 11 mg/L; coliformes &gt; 1,000 y &gt; 200 NMP/100 mL; SDT y conductividad &gt; 2,000) → (4) conteos y porcentajes con el número de sitios con dato como denominador → (5) comparación pozo vs cenote con medianas (los valores son muy asimétricos) → (6) gráficas en matplotlib. Todo es descriptivo; no se infieren causas."))
s.append(P("4. Resultados", h))
s.append(Image(str(F / "fig1_mapa_nitratos.png"), width=W * .74, height=W * .74 * 4.3 / 7.2))
s.append(P("Figura 1. Solo 3 pozos rebasan 11 mg/L; 45 más están entre 5 y 11 mg/L (amarillo), repartidos en el centro-norte y sur del estado. Mediana estatal: 4.28 mg/L; percentil 90: 7.7 mg/L.", small))
row = Table([[Image(str(F / "fig2_coliformes_pozo_cenote.png"), width=W * .32, height=W * .32 * 3.4 / 3.6),
              Image(str(F / "fig3_semaforo.png"), width=W * .32, height=W * .32 * 3.4 / 3.6),
              Image(str(F / "fig4_salinidad.png"), width=W * .32, height=W * .32 * 3.4 / 3.6)]], colWidths=[W / 3] * 3)
s.append(row)
s.append(P("Figura 2. Los 8 cenotes tienen coliformes fecales detectados (mediana 256 NMP/100 mL; 5 de 8 arriba de 200), mientras que en los 80 pozos con dato la mediana es 2. Figura 3. Yucatán tiene menos sitios en rojo (4 %) que el país (37 %), pero más en amarillo (40 % contra 18 %), sobre todo por dureza y conductividad. Figura 4. 29 sitios (24 %) son ligeramente salobres o más (SDT &gt; 1,000 mg/L) y 21 incumplen conductividad (&gt; 2,000 µS/cm), sobre todo en el poniente y la costa; solo 2 incumplen SDT (Chapab y Celestún).", small))
irows = [["Indicador (valor del periodo 2012–2025)", "Sitios", "Con dato", "%"]] + [[r.indicador, r.sitios, r.sitios_con_dato, f"{r.porcentaje:.1f}"] for r in ind.itertuples()]
s.append(tbl(irows, [W * .6, W * .13, W * .14, W * .13]))
s.append(P("Sitios prioritarios (5 más altos por parámetro)", h))
trows = [["Criterio", "Sitio", "Municipio", "Tipo", "N-NO₃ mg/L", "Colif. NMP/100 mL", "Semáforo"]]
for r in top.groupby("ranking", sort=False).head(5).itertuples():
    trows.append([r.ranking, r.sitio.title()[:48], r.municipio.title(), r.subtipo.title(), f"{float(r.n_no3_mgL):.2f}", r.cf_nmp100 or "sin dato", r.semaforo.title()])
s.append(tbl(trows, [W * .14, W * .33, W * .12, W * .08, W * .1, W * .12, W * .11]))
s.append(P("5. Hallazgo e interpretación", h))
s.append(bl("<b>Observado:</b> el incumplimiento por nitratos es puntual (3 de 121 sitios), pero un 40 % de los sitios ya perdió la categoría «excelente» (&gt; 5 mg/L). Ningún sitio rebasa 1,000 NMP/100 mL, pero los coliformes fecales se detectan en 57 % de los sitios con dato y los valores más altos están en cenotes."))
s.append(bl("<b>Interpretación:</b> la señal de contaminación es más bien difusa y de nivel medio que crítica; los cenotes, más expuestos a la superficie, son los puntos más sensibles a contaminación fecal. Las 3 alertas de nitratos son candidatas a vigilancia prioritaria."))
s.append(bl("<b>Implicación para la audiencia:</b> priorizar vigilancia en Halachó, Motul y Tepakán (nitratos) y en cenotes de uso recreativo o comunitario (coliformes), y cerrar huecos de monitoreo: 33 sitios sin coliformes (las claves más recientes de la red, OCPYU6437 en adelante, en su mayoría sistemas de agua potable) y ningún sitio de Yucatán en el reporte anual 2025."))
s.append(P("6. Límites", h))
s.append(bl("Un valor por sitio para 2012–2025: oculta variaciones entre años y temporadas, y el archivo no documenta si es promedio u otra medida; para coliformes los decimales sugieren una media geométrica (por confirmar)."))
s.append(bl("Solo 8 cenotes: la diferencia pozo–cenote es descriptiva y no generalizable. Los sitios no son una muestra aleatoria del acuífero; los resultados describen la red, no todo Yucatán."))
s.append(bl("Agua cruda, no agua de la llave; sin datos de exposición ni de salud. No se atribuyen causas (granjas, fosas sépticas, agricultura): no están en los datos."))
s.append(bl("Comparación nacional con el mismo archivo (2,753 sitios con semáforo); 122 sitios nacionales sin semáforo quedan fuera."))
s.append(P("7. Archivos para verificar y uso de IA", h))
s.append(P("<b>datos/</b> yucatan_subterranea_2012-2025_extracto.csv (extracto original), sitios_yucatan_limpio.csv (base para Tableau), resumen_*.csv · <b>scripts/</b> extraccion_navegador.js (extracción del Excel), analisis.py (verificación, limpieza, tablas y figuras), build_pdf.py · <b>figs/</b> PNG de las figuras. Reproducir: <font face='Sans'>python scripts/analisis.py</font>."))
s.append(P("<b>Uso de IA:</b> se usó Claude (Anthropic) para extraer los datos del archivo oficial, escribir los scripts de análisis, generar las figuras y redactar este reporte. El equipo debe revisar los resultados con los scripts y el archivo original antes de presentarlos.", small))
def foot(c, d):
    c.saveState(); c.setFont("Sans", 7); c.setFillColor(GRAY)
    c.drawString(.6 * inch, .45 * inch, "Datostada MX 2026 · Evidence Board · Equipo Los Ternurines · Fuente: CONAGUA, RENAMECA")
    c.drawRightString(letter[0] - .6 * inch, .45 * inch, f"Página {d.page}"); c.restoreState()
doc = SimpleDocTemplate(out, pagesize=letter, leftMargin=.6 * inch, rightMargin=.6 * inch, topMargin=.5 * inch, bottomMargin=.65 * inch,
                        title="Evidence Board – El agua que no vemos")
doc.build(s, onFirstPage=foot, onLaterPages=foot)
print("ok")
