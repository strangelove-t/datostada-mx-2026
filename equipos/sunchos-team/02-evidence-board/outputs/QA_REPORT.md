# QA/QC Audit Report — Team Sunchos (Fase 02 Explore)

- **Estado Global:** PASS (100%)
- **Compuertas aprobadas:** 16 / 16

| Gate | Estado | Evidencia verificada |
|---|---|---|
| PK dim_sitio (site_id unico, n=121) | **PASS** | `n=121, unique=121, nulls=0` |
| PK dim_municipio (cve_mun unico, n=106) | **PASS** | `n=106, unique=106, nulls=0` |
| PK dim_parametro (param_code unico, n=4) | **PASS** | `n=4, codes=['N_NO3', 'COLI_FEC', 'SDT', 'CONDUCT']` |
| PK fact_calidad_sitio (fact_id unico, n=451) | **PASS** | `n=451, unique=451, nulls=0` |
| FK fact.site_id -> dim_sitio.site_id | **PASS** | `huerfanos=0` |
| FK fact.param_code -> dim_parametro.param_code | **PASS** | `huerfanos=0` |
| FK dim_sitio.cve_mun -> dim_municipio.cve_mun | **PASS** | `nulls=0, huerfanos=0` |
| Consistencia conteo municipal (solo sitios dentro poligono INEGI Yucatan) | **PASS** | `sum(dim_municipio.n_sitios_renameca)=119, dim_sitio[dentro_poligono_yucatan]=119` |
| Coordenadas en bounding box Yucatan y distancias >= 0 | **PASS** | `lat=[20.0677, 21.4091], lon=[-90.2356, -87.6113]` |
| Suma de usos de suelo terrestres (Urbano+Agro+Natural = 100% +/- 0.1) | **PASS** | `min=99.99%, max=100.01%` |
| QC fisicoquimico SDT / Conductividad en rango valido [0.40, 0.80] | **PASS** | `qc_all_true=True, rango=[0.4186, 0.7752]` |
| Cero valores censurados (<LD) marcados falsamente como rebase | **PASS** | `casos=0` |
| Consistencia de conteo de rebases entre fact_calidad_sitio y dim_sitio | **PASS** | `fact={'COLI_FEC': 50, 'CONDUCT': 21, 'N_NO3': 3, 'SDT': 29}, dim=(N_NO3:3, COLI_FEC:50, SDT:29)` |
| Capas GeoJSON listas para Tableau | **PASS** | `municipios_yucatan.geojson(n=106, valid=True) | reserva_anillo_cenotes_2025.geojson(n=1, valid=True) | sitios_yucatan.geojson(n=121, valid=True)` |
| Inmutabilidad 01_raw verificada por SHA-256 vs MANIFEST_FUENTES.csv | **PASS** | `verificados=13/13, discrepancias=0` |
| Artefactos EDA generados (tablas CSV y figuras PNG) | **PASS** | `tablas_csv=12, figuras_faltantes=[]` |
