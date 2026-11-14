# Muestra verificable de datos — Team Sunchos (Fase 02 · Explore)

Por lineamiento de tamaño de repositorio, los archivos crudos oficiales (`data/01_raw/`, incluido USV Serie VII de 308 MB) y las tablas completas procesadas (`data/02_staging/`, `03_curated/`, `04_analytics_bi/`) se excluyen de Git en esta entrega y se alojarán por separado / empaquetados en el `.twbx` de la Fase 03.

Esta carpeta contiene la **muestra estratificada verificable** del Modelo Estrella y la trazabilidad completa de fuentes:

- `MANIFEST_FUENTES.csv`: URLs oficiales, fechas de descarga, tamaño en bytes y SHA-256 de los 13 insumos reales de CONAGUA, Diario Oficial de Yucatán, INEGI y Secretaría de Economía.
- `dim_parametro.csv`: Catálogo normativo completo (4 parámetros: `N_NO3`, `COLI_FEC`, `SDT`, `CONDUCT`).
- `dim_sitio_muestra.csv`: Muestra estratificada de **15 sitios** (sobre el universo real de 121) cubriendo Pozos y Cenotes, Dentro/Fuera del Anillo, zonas de Recarga/Tránsito/Descarga, los 4 entornos de 2 km (Opción A), casos `<LD`, rebases NOM-127 y control fronterizo.
- `fact_calidad_sitio_muestra.csv`: **60 hechos** asociados a esos 15 sitios.
- `dim_municipio_muestra.csv`: **11 municipios** correspondientes a la muestra.
