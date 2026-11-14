# Dos mapas bajo Yucatán · Dashboard · Sapos AI

Reto Yucatán Vivo · El agua que no vemos. Qué tiene el agua subterránea monitoreada de Yucatán,
dónde, y qué tratamiento pide. Pensado para quien decide dónde vigilar y qué tratamiento poner:
organismos operadores de agua, servicios de salud y ayuntamientos.

## Contenido

| Ruta | Qué es |
| --- | --- |
| `sapos-ai-dos-mapas-bajo-yucatan.twbx` | Libro de Tableau empaquetado, con los datos incorporados (tabla y extracto) |
| `sapos-ai-dos-mapas-bajo-yucatan-respaldo.pdf` | Respaldo en PDF: las dos vistas y un ejemplo de filtro (3 páginas) |
| `datos/derivados/` | Tablas de Yucatán extraídas del archivo de CONAGUA y cifras del tablero |
| `datos/peninsula.geojson` | Contorno del estado (Natural Earth, dominio público) |
| `analisis/` | Scripts que calculan las cifras y arman la tabla del tablero |
| `analisis/pruebas/test_tablero.py` | Pruebas que recalculan cada cifra del tablero desde los muestreos |

## Cómo abrirlo

Abrir el `.twbx` con Tableau Public o Tableau Desktop (probado en Tableau Public 2026.3). No pide
conexión ni archivos externos. Abre en la vista principal; la segunda vista está en la pestaña
«Cuándo».

## Cómo se usa

| Acción | Qué pasa |
| --- | --- |
| Clic en una de las cuatro cifras (51, 13, 5, 52) | El mapa, los perfiles y la lista de municipios muestran solo los sitios de esa clase. Otro clic lo quita |
| Clic en el nombre de un municipio de la lista | Todo el tablero muestra solo ese municipio (un clic en un segmento de su barra deja solo los sitios de esa clase) |
| Clic en un sitio del mapa | El mismo sitio se resalta en los dos perfiles |
| Cursor sobre un sitio | Ficha del sitio: nombre, municipio, pozo o cenote, qué atender, cuántos de sus muestreos pasan cada referencia y de qué año a qué año se midió |
| En «Cuándo», clic en una fila | El mismo sitio se resalta en las dos franjas |

## Qué muestra

**Vista principal.** Las sales son más frecuentes hacia el poniente; las bacterias fecales no
siguen ese mapa.

- Mapa de los 121 sitios. Color: qué atender en el sitio. Forma: círculo para pozo, rombo para
  cenote. Tamaño: número de muestreos (de 2 a 28). El contorno del estado es aproximado (Natural
  Earth); no se usa mapa de fondo.
- Dos perfiles de poniente a oriente con la misma escala: porcentaje de muestreos de cada sitio
  con sólidos disueltos sobre 1,000 mg/L, y porcentaje con coliformes fecales. La línea es el
  promedio de los 17 sitios vecinos, calculado con todos los sitios. Correlación de Spearman con
  la longitud: −0.54 para los sólidos disueltos (121 sitios) y −0.02 para las bacterias (88 sitios
  con medición; con la latitud, 0.03). En cenotes hay coliformes fecales en 79.4 % de 97
  muestreos; en pozos, en 27.5 % de 505.
- Cuatro cifras: 51 sitios con sales o dureza recurrentes, 13 con bacterias, 5 con ambos y 52 con
  ninguno en lo medido.
- Lista de los 65 municipios monitoreados, ordenada por sitios con algo recurrente. La etiqueta
  («Mérida · 13 de 19») describe al municipio completo y no cambia con el filtro.

**Vista «Cuándo».** Cada fila es un sitio, de poniente (arriba) a oriente (abajo); cada columna,
un año.

- 94 de 121 sitios mantienen su estado de sólidos disueltos todos los años en que se midieron (23
  siempre sobre la referencia, 71 nunca); 27 cambian.
- 48 de 88 sitios con medición de coliformes fecales cambian de un año a otro; 3 los tienen todos
  los años y 37 nunca.
- En los 30 sitios con 8 años o más de datos, 15 mantienen su estado de sólidos disueltos y 2 el
  de bacterias.
- Coliformes fecales sobre 1,000 NMP/100 mL (umbral de la clasificación de CONAGUA): 0 de 88
  sitios con la media geométrica del sitio; 19 sitios con al menos un muestreo.

El tablero separa lo observado, la interpretación y la implicación en el panel de «Cuándo» y en el
recuadro de la vista principal.

## Definiciones

- **Referencias**: NOM-127-SSA1-2021. Sólidos disueltos totales, 1,000 mg/L; dureza total,
  500 mg/L como CaCO₃; coliformes fecales, cualquier detección.
- **Excedencia**: valor mayor que la referencia. Un valor reportado con `<` cuenta como no
  detectado y nunca como excedencia; uno con `>` cuenta como detección.
- **Recurrente**: en la mitad o más de los muestreos del sitio con medición.
- **Qué atender**: «Sales o dureza» si los sólidos disueltos o la dureza son recurrentes;
  «Bacterias» si lo son los coliformes fecales; «Ambos»; «Ninguno recurrente».
- **Estado del año**: sobre la referencia si algún muestreo de ese año la pasa. Los perfiles y la
  vista «Cuándo» usan solo sólidos disueltos; la clase «Sales o dureza» incluye además la dureza.

## Límites

- Es agua del acuífero sin tratar, no la que sale de la llave.
- La red no es una muestra al azar: cubre 65 de 106 municipios y hay más sitios cerca de Mérida.
  La lista de municipios ordena por número de sitios, no por población ni por gravedad.
- 33 sitios no tienen medición de coliformes fecales: 18 están en «Sales o dureza» y 15 en
  «Ninguno recurrente». Los coliformes se midieron hasta octubre de 2022.
- 56 sitios tienen solo 2 muestreos; en ellos «recurrente» puede ser 1 de 2.
- En 432 de 523 casos, el estado de un sitio en un año sale de un solo muestreo.
- El límite de detección de coliformes cambió entre periodos (de <1 a <30 NMP/100 mL). Con un
  umbral común de 30, cambian de un año a otro 37 de 88 sitios en lugar de 48.
- Un sitio (`OCPYU5381`, pozo del sistema de agua potable de Peto) viene asignado a Mérida en la
  fuente. El tablero lo cuenta en Peto, donde lo ubican su nombre y sus coordenadas; por eso aquí
  son 65 municipios y en el Evidence Board, 64.
- El tablero describe; no explica causas ni mide riesgo para la salud.

## Cómo verificarlo

Requisitos: Python 3.12 y los paquetes de `analisis/requisitos.txt`.

```
pip install -r analisis/requisitos.txt
python analisis/04_cifras_tablero.py datos/derivados
python analisis/05_tabla_tablero.py datos/derivados datos/peninsula.geojson salida
python -m pytest analisis/pruebas -q
```

Resultado esperado: `cifras_tablero.json` y `sitio_anio.csv` se regeneran iguales, `salida/`
recibe la tabla del tablero y todas las pruebas pasan (una se omite si no está instalado
`tableauhyperapi`, que solo se usa para leer el extracto). Las pruebas abren el `.twbx`, leen su
tabla y sus textos, y los comparan con las cifras recalculadas desde los 683 muestreos.

`resultados_yucatan.csv` y `sitios_yucatan.csv` son el recorte de Yucatán del archivo original
`Subterraneo.xlsb`, tal como viene en la fuente; los scripts que lo producen están en
`02-evidence-board/analisis/`.

## Fuentes

- CONAGUA, Red Nacional de Medición de Calidad del Agua (RENAMECA), resultados de agua
  subterránea, 24 de noviembre de 2012 a 15 de noviembre de 2023. Descarga del 13 de noviembre
  de 2026.
- Secretaría de Salud, NOM-127-SSA1-2021 (DOF, 2 de mayo de 2022), tablas 2, 4, 5 y 6.
- Natural Earth, límites estatales a escala 1:10 millones.

## Uso de herramientas

Análisis en Python y tablero en Tableau. El equipo usó un asistente de IA (Claude, de Anthropic)
como acompañamiento: apoyo en la preparación de la tabla de datos, verificación de cifras y
revisión de redacción. La pregunta, la interpretación de resultados y el diseño del tablero son
decisiones del equipo.
