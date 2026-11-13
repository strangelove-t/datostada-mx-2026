# Dos mapas bajo Yucatán · Evidence Board · Sapos AI

Reto Yucatán Vivo · El agua que no vemos. Esta carpeta contiene el reporte y todo lo necesario
para verificar sus cifras desde el archivo original de CONAGUA.

## Contenido

| Ruta | Qué es |
| --- | --- |
| `sapos-ai-evidence-board.pdf` | El reporte (3 páginas) |
| `datos/Subterraneo.xlsb` | Archivo original de RENAMECA (CONAGUA), agua subterránea, descargado el 13 nov 2026 |
| `datos/peninsula.geojson` | Contorno de Yucatán, Campeche y Quintana Roo (Natural Earth, dominio público) |
| `datos/derivados/` | Tablas de Yucatán y cifras calculadas (se regeneran con los scripts) |
| `analisis/` | Scripts de conversión, recorte y cálculo |
| `analisis/pruebas/test_evidence.py` | Pruebas que recalculan cada cifra del reporte desde el archivo original |
| `documento/` | Fuente del PDF (`evidence-board.html`) y sus figuras |

## Tablas derivadas

| Archivo | Contenido |
| --- | --- |
| `sitios_yucatan.csv` | Los 121 sitios de Yucatán |
| `resultados_yucatan.csv` | Los 683 muestreos, con todos los parámetros tal como vienen en la fuente |
| `sitios_resumen.csv` | Un renglón por sitio: zona, subtipo, muestreos, excedencias y clase por parámetro |
| `tendencia_sdt_sitios_largos.csv` | Prueba de Mann-Kendall por sitio (30 sitios con ocho o más años) |
| `cifras_evidence_board.json` | Todas las cifras del reporte |

## Cómo reproducirlo

Requisitos: Python 3.12 y los paquetes de `analisis/requisitos.txt`.

```
pip install -r analisis/requisitos.txt
python analisis/01_convertir.py datos/Subterraneo.xlsb datos/derivados
python analisis/02_recorte_yucatan.py datos/derivados
python analisis/03_evidence_board.py datos/derivados datos/peninsula.geojson documento
python -m pytest analisis/pruebas -q
```

Resultado esperado: las tablas de `datos/derivados/` y las figuras de `documento/` se regeneran
iguales, y todas las pruebas pasan. El primer paso crea además tres tablas nacionales que no se
incluyen aquí por tamaño.

Para regenerar el PDF, abrir `documento/evidence-board.html` en un navegador e imprimirlo a PDF
en tamaño carta.

## Definiciones

- **Excedencia**: valor mayor que el límite de la NOM-127-SSA1-2021. Un valor reportado con `<`
  cuenta como no detectado y nunca como excedencia; uno con `>` cuenta como detección.
- **Zonas**: franjas de longitud. Poniente (al oeste de 89.9° O), Franja de Mérida (89.9° a
  89.3° O), Centro (89.3° a 88.6° O) y Oriente (al este de 88.6° O). Es una división descriptiva
  del equipo.
- **Clase por sitio**: «nunca», «a veces» o «en la mitad o más de sus muestreos».
- **Tendencia**: prueba de Mann-Kendall sobre la mediana anual de sólidos disueltos totales de
  cada sitio con ocho o más años de datos; significativa si p < 0.05.

## Fuentes

- CONAGUA, Red Nacional de Medición de Calidad del Agua (RENAMECA), resultados de agua subterránea.
- Secretaría de Salud, NOM-127-SSA1-2021 (DOF, 2 de mayo de 2022), tablas 2, 4, 5 y 6.
- Natural Earth, límites estatales a escala 1:10 millones.

## Uso de herramientas

Análisis en Python. El equipo usó un asistente de IA (Claude, de Anthropic) como acompañamiento:
búsqueda y revisión de fuentes, apoyo en la limpieza de datos y en los cálculos, verificación de
cifras y revisión de redacción. La pregunta, la interpretación de resultados y el diseño
del dashboard son decisiones del equipo.
