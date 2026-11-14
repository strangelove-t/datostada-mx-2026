# Guía rápida: Dashboard en Tableau · "El agua que no vemos"
Equipo Los Ternurines · Datostada MX 2026 · Entrega 3 (cierra **sábado 14 nov, 12:00 p.m.**)

Tiempo estimado: 45–60 min. Archivo de datos: `datos/tableau_sitios_indicadores.csv`
(363 filas = 121 sitios × 3 indicadores; una fila por sitio e indicador).

## Diseño objetivo (una vista principal)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ¿Dónde vigilar el agua subterránea de Yucatán?            [subtítulo]   │
│ [Indicador ▼]  [Tipo de sitio ▼]   | Sitios | Incumplen | Atención | Sin dato |
├───────────────────────────────────────────────┬──────────────────────────┤
│                                               │  Sitios por nivel (barras)│
│            MAPA de sitios                     │  ← clic = filtra todo     │
│   color = nivel, forma = pozo/cenote          ├──────────────────────────┤
│   clic/hover = resalta el sitio               │  Top 10 sitios (barras)   │
│                                               │  con línea del límite     │
├───────────────────────────────────────────────┴──────────────────────────┤
│ Fuente · Unidades · Periodo · Límites · Uso de IA                         │
└──────────────────────────────────────────────────────────────────────────┘
```

Colores de **Nivel** (usar los mismos en todas las hojas):
Incumple `#C0392B` · Atención `#E0A030` · Dentro de rango `#7FB3C0` · Sin dato `#C8C8C8`

---

## 1. Conectar los datos
1. Conectar → **Archivo de texto** → `tableau_sitios_indicadores.csv`.
2. En la pestaña de datos revisa los tipos:
   - `latitud`: Número decimal → clic en el ícono → **Función geográfica → Latitud**.
   - `longitud`: Número decimal → **Función geográfica → Longitud**.
   - `valor`, `limite`, `nivel_orden`: Número decimal.
   - Todo lo demás: Cadena.

## 2. Campos calculados (Análisis → Crear campo calculado)
```
Sitios            = COUNTD([clave])
Sitios incumplen  = COUNTD(IF [nivel] = "Incumple" THEN [clave] END)
Sitios atencion   = COUNTD(IF [nivel] = "Atención" THEN [clave] END)
Sitios sin dato   = COUNTD(IF [nivel] = "Sin dato" THEN [clave] END)
```

## 3. Hoja "Mapa"
1. Doble clic en `longitud` y `latitud` (Tableau dibuja el mapa de Yucatán).
2. Desactiva la agregación: Análisis → **Agregar medidas** (desmarcar), o arrastra `clave` a **Detalle**.
3. `nivel` → **Color** (asigna los colores de arriba). `subtipo` → **Forma** (círculo = Pozo, triángulo = Cenote).
4. `indicador` → **Filtros** → selecciona "Nitrógeno de nitratos" → clic derecho en el filtro:
   - **Mostrar filtro**, tipo **Lista desplegable de valor único**.
   - **Agregar a contexto** (importante para el Top 10).
   - **Aplicar a hojas de trabajo → Todas las que usan esta fuente de datos**.
5. `subtipo` → Filtros → Mostrar filtro → también **Agregar a contexto** y **Aplicar a todas las hojas**.
6. **Tooltip** (descripción emergente), pega y ajusta:
```
<sitio> · <subtipo>, <municipio>
<indicador>: <valor_texto>
Clasificación CONAGUA: <clasificacion_conagua>
—
Nitratos: <nitratos_txt> | Coliformes fecales: <coliformes_txt> | SDT: <sdt_txt>
Semáforo CONAGUA: <semaforo>   Contaminantes: <contaminantes>
<obs_calidad>
```
   (Arrastra antes `valor_texto`, `clasificacion_conagua`, `nitratos_txt`, `coliformes_txt`,
   `sdt_txt`, `semaforo`, `contaminantes`, `obs_calidad`, `sitio`, `municipio` a **Información sobre herramientas**.)
7. Mapa → Capas de mapa: estilo "Claro"; sube el tamaño de las marcas un poco.

## 4. Hoja "Niveles"
1. `nivel` → Filas; `Sitios` (calculado) → Columnas.
2. Ordena `nivel` por `nivel_orden` (clic derecho en `nivel` → Ordenar → Campo → nivel_orden, mínimo, ascendente).
3. `nivel` → Color; `Sitios` → Etiqueta.
4. Título: "Sitios por nivel · clic para filtrar".

## 5. Hoja "Top 10"
1. `sitio_etiqueta` → Filas; `valor` (SUMA) → Columnas; orden descendente.
2. `sitio_etiqueta` → Filtros → pestaña **Superior** → Por campo → Superior **10** por SUMA(valor).
   (Funciona por indicador porque `indicador` está en contexto; si no, el Top 10 sale mal.)
3. `nivel` → Color; `valor_texto` → Etiqueta; `clave` → Detalle.
4. Pestaña **Análisis** → **Línea de referencia** → Por tabla → valor **Promedio de limite**,
   etiqueta "Límite", línea roja punteada.
5. Título: "Sitios con valores más altos".

## 6. Hoja "Resumen" (KPIs)
1. Arrastra `Sitios`, `Sitios incumplen`, `Sitios atencion`, `Sitios sin dato` a **Texto**
   (Tableau crea Nombres de medidas / Valores de medidas).
2. `Nombres de medidas` → Columnas. Formato grande (18–24 pt). Oculta encabezados de fila.

## 7. Dashboard
1. Nuevo dashboard → Tamaño **Fijo 1400 × 850** (o "Automático").
2. Arrastra: Texto (título) arriba → Resumen → Mapa (izquierda, grande) → Niveles y Top 10 (derecha) → Texto de notas (abajo).
3. Muestra los filtros `indicador` y `subtipo` arriba (deben decir "Todas las que usan esta fuente").
4. **Acciones** (Dashboard → Acciones):
   - **Filtro** "Filtrar por nivel": origen *Niveles*, destino *Mapa* y *Top 10*, ejecutar al **Seleccionar**,
     al borrar la selección → **Mostrar todos los valores**.
   - **Resaltado** "Resaltar sitio": origen *Mapa* y *Top 10*, destino todas, al **Pasar el cursor**,
     campos seleccionados → `clave`.
5. Prueba: cambia el indicador, haz clic en "Incumple" (deben quedar 3 sitios en nitratos), pasa el cursor
   por un sitio del Top 10 y verifica que se resalte en el mapa.

## 8. Textos para pegar
**Título:** ¿Dónde vigilar el agua subterránea de Yucatán?

**Subtítulo:** Nitratos, coliformes fecales y salinidad en los 121 sitios de monitoreo de CONAGUA en Yucatán · valor por sitio del periodo 2012–2025. Elige un indicador, haz clic en un nivel para filtrar y pasa el cursor sobre un sitio.

**Notas (pie):**
Fuente: CONAGUA, Red Nacional de Medición de Calidad del Agua (RENAMECA), «Calidad del Agua Subterránea», archivo Calidad_del_Agua_Subterr_nea_p_2012-2025.xlsx (gob.mx/conagua), descargado el 13/11/2026.
Unidades: nitrógeno de nitratos y sólidos disueltos totales en mg/L; coliformes fecales en NMP/100 mL.
Niveles (escalas CONAGUA): nitratos ≤5 dentro de rango, 5–11 atención, >11 incumple · coliformes ≤200, 200–1,000, >1,000 · SDT ≤1,000, 1,000–2,000, >2,000. "<1" = no detectado.
Periodo: un solo valor por sitio para 2012–2025; no muestra cambios entre años. El archivo anual 2025 no incluye sitios de Yucatán.
Límites: mide agua cruda del acuífero, no agua de la llave; los sitios no son una muestra aleatoria; 33 sitios sin dato de coliformes; solo 8 cenotes; no se atribuyen causas.
Equipo Los Ternurines · Datostada MX 2026 · Uso de IA: Claude (Anthropic) apoyó la preparación de datos y esta guía; el equipo construyó y verificó el dashboard.

## 9. Cifras para verificar que todo cuadra
| Indicador | Incumple | Atención | Dentro de rango | Sin dato |
|---|---|---|---|---|
| Nitrógeno de nitratos | 3 | 45 | 73 | 0 |
| Coliformes fecales | 0 | 6 | 82 | 33 |
| Sólidos disueltos totales | 2 | 27 | 92 | 0 |

## 10. Entregar (antes de las 12:00)
1. **PDF de respaldo:** con "Nitrógeno de nitratos" seleccionado → Archivo → **Imprimir a PDF** (o Exportar → PDF)
   → `El_agua_que_no_vemos_dashboard.pdf`. Si da tiempo, exporta otro con "Coliformes fecales".
2. **Empaquetado:** Archivo → **Exportar libro de trabajo empaquetado** → `El_agua_que_no_vemos.twbx`
   (incluye los datos). Ábrelo de nuevo para comprobar que abre.
3. Sube a GitHub, carpeta `03 Dashboard en Tableau`: el `.twbx`, el PDF, la carpeta `datos/`, esta guía y `LEEME.md`.
   Haz commit y push **antes de las 12:00** y revisa en la web de GitHub que los archivos estén ahí.
