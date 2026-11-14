# 03 Dashboard en Tableau · El agua que no vemos
Equipo Los Ternurines (Acosta Kevin, Damaris Ramirez, Esteban Priego, Jose Samos, Arturo Suarez) · Datostada MX 2026

- `El_agua_que_no_vemos.twbx`: libro empaquetado de Tableau con los datos incorporados (`Data/datos/dashboard_sitios.csv`).
  Vista principal: mapa de los 121 sitios coloreado por nivel de nitratos; visualizaciones conectadas: sitios por nivel de
  nitratos y de coliformes fecales; interacción: clic en una barra de "Nitratos por nivel" filtra el mapa; descripciones emergentes por sitio.
- `El_agua_que_no_vemos_dashboard.pdf`: PDF de respaldo (vista estática del dashboard con los mismos datos).
- `datos/dashboard_sitios.csv`: datos del libro (un renglón por sitio). `datos/tableau_sitios_indicadores.csv`: versión larga
  (sitio × indicador). `datos/sitios_yucatan_limpio.csv` y `datos/yucatan_subterranea_2012-2025_extracto.csv`: datos de la Entrega 2.
- `GUIA_construccion_dashboard.md`: diseño, campos y cifras de control.

Fuente: CONAGUA, RENAMECA, «Calidad del Agua Subterránea», Calidad_del_Agua_Subterr_nea_p_2012-2025.xlsx (gob.mx/conagua), descargado el 13/11/2026.
Unidades: N-NO3 y SDT en mg/L; coliformes fecales en NMP/100 mL. Periodo: un valor por sitio para 2012–2025.
Niveles (escalas CONAGUA): nitratos ≤5 / 5–11 / >11 mg/L; coliformes ≤200 / 200–1,000 / >1,000 NMP/100 mL.
Límites: agua cruda del acuífero (no de la llave); sitios no aleatorios; 33 sitios sin dato de coliformes; solo 8 cenotes; no se atribuyen causas.
Uso de IA: Claude (Anthropic) generó el libro .twbx, el PDF de respaldo y la preparación de datos; el equipo los revisó.
