# 02 Evidence Board · El agua que no vemos (Datostada MX 2026)

- `Evidence_Board_El_agua_que_no_vemos.pdf`: entregable (3 páginas).
- `datos/yucatan_subterranea_2012-2025_extracto.csv`: los 121 sitios de Yucatán extraídos del archivo oficial de CONAGUA
  `Calidad_del_Agua_Subterr_nea_p_2012-2025.xlsx` (https://www.gob.mx/cms/uploads/attachment/file/1084131/Calidad_del_Agua_Subterr_nea_p_2012-2025.xlsx).
- `datos/sitios_yucatan_limpio.csv`: base limpia con variables derivadas (para Tableau).
- `datos/resumen_*.csv`: tablas que respaldan cada cifra del reporte.
- `scripts/extraccion_navegador.js`: extracción del Excel oficial (consola del navegador en www.gob.mx).
- `scripts/analisis.py`: verificación con sumas de control, limpieza, tablas y figuras → `python scripts/analisis.py`
- `scripts/build_pdf.py`: genera el PDF → `python scripts/build_pdf.py . Evidence_Board_El_agua_que_no_vemos.pdf`
- `figs/`: figuras en PNG.

Requisitos: Python 3 con pandas, numpy, matplotlib (y reportlab para el PDF).
Equipo: Los Ternurines (Acosta Kevin, Damaris Ramirez, Esteban Priego, Jose Samos, Arturo Suarez).
Uso de IA: Claude (Anthropic) apoyó la extracción, los scripts, las figuras y la redacción
