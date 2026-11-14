"""Configuracion centralizada y catalogos oficiales para Team Sunchos (Fase 02 - Explore)."""
from pathlib import Path
import unicodedata

# Rutas del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "01_raw"
STAGING_DIR = DATA_DIR / "02_staging"
CURATED_DIR = DATA_DIR / "03_curated"
BI_DIR = DATA_DIR / "04_analytics_bi"
OUTPUT_DIR = BASE_DIR / "outputs"
FIG_DIR = OUTPUT_DIR / "figures"
TAB_DIR = OUTPUT_DIR / "tables"

for d in [STAGING_DIR, CURATED_DIR, BI_DIR, FIG_DIR, TAB_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Sistemas de Referencia Espacial
CRS_WGS84 = "EPSG:4326"
CRS_METRIC = "EPSG:32616"  # WGS 84 / UTM Zone 16N (estandar metrico para Yucatan y Decreto 88/2025)

# Limites NOM-127-SSA1-2021 (referencia para agua de consumo humano)
NOM127_LIMITS = {
    "N_NO3": {
        "nombre": "Nitrogeno de nitratos (N-NO3)",
        "unidad": "mg/L",
        "limite": 11.0,
        "criterio": "> 11.0 mg/L",
        "grupo_semaforo": "Rojo (Critico)",
    },
    "COLI_FEC": {
        "nombre": "Coliformes fecales",
        "unidad": "NMP/100 mL",
        "limite": 0.0,
        "criterio": "Presencia (> 0 / no ausente en 100 mL)",
        "grupo_semaforo": "Rojo (Critico)",
    },
    "SDT": {
        "nombre": "Solidos Disueltos Totales (SDT)",
        "unidad": "mg/L",
        "limite": 1000.0,
        "criterio": "> 1,000 mg/L",
        "grupo_semaforo": "Amarillo (Salinizacion)",
    },
    "CONDUCT": {
        "nombre": "Conductividad electrica",
        "unidad": "uS/cm",
        "limite": 2000.0,
        "criterio": "> 2,000 uS/cm (referencia CONAGUA riego: dudosa/indeseable; NOM-127 no fija limite)",
        "grupo_semaforo": "Amarillo (Salinizacion)",
    },
}

# Decreto 117/2013 (13 municipios originales de la Reserva Estatal)
MUN_DECRETO_2013 = {
    "ACANCEH", "CUZAMA", "HOCABA", "HOCTUN", "HOMUN", "HUHI",
    "SANAHCAT", "SEYE", "TAHMEK", "TECOH", "TEKIT", "TIMUCUY", "XOCCHEL",
}

# Decreto 88/2025 (24 municipios: 13 principales + 11 ampliados con porciones)
MUN_DECRETO_2025_PORCIONES = {
    "ABALA", "CACALCHEN", "CHAPAB", "CHUMAYEL", "IZAMAL", "SOTUTA",
    "KANTUNIL", "MAMA", "MAYAPAN", "TIXKOKOB", "TIXPEHUAL",
}
MUN_DECRETO_2025 = MUN_DECRETO_2013 | MUN_DECRETO_2025_PORCIONES

# Unidad Geohidrologica Anillo de Cenotes (54 municipios por zona y subzona, Decreto 88/2025 p. 4)
UNIDAD_GEO_54 = {
    # Recarga
    "SEYE": ("Recarga", "Subzona 1"),
    "ACANCEH": ("Recarga", "Subzona 1"),
    "TIMUCUY": ("Recarga", "Subzona 1"),
    "HOMUN": ("Recarga", "Subzona 1"),
    "CUZAMA": ("Recarga", "Subzona 1"),
    "TECOH": ("Recarga", "Subzona 1"),
    "TEKIT": ("Recarga", "Subzona 1"),
    "TAHMEK": ("Recarga", "Subzona 2"),
    "HOCTUN": ("Recarga", "Subzona 2"),
    "XOCCHEL": ("Recarga", "Subzona 2"),
    "HOCABA": ("Recarga", "Subzona 2"),
    "SANAHCAT": ("Recarga", "Subzona 2"),
    "HUHI": ("Recarga", "Subzona 2"),
    # Transito - Subzona 1
    "CHICXULUB PUEBLO": ("Transito", "Subzona 1"),
    "MOCOCHA": ("Transito", "Subzona 1"),
    "MERIDA": ("Transito", "Subzona 1"),
    "UCU": ("Transito", "Subzona 1"),
    "CONKAL": ("Transito", "Subzona 1"),
    "TIXPEHUAL": ("Transito", "Subzona 1"),
    "KANASIN": ("Transito", "Subzona 1"),
    "UMAN": ("Transito", "Subzona 1"),
    # Transito - Subzona 2
    "MOTUL": ("Transito", "Subzona 2"),
    "TELCHAC PUEBLO": ("Transito", "Subzona 2"),
    "BACA": ("Transito", "Subzona 2"),
    "MUXUPIP": ("Transito", "Subzona 2"),
    "YAXKUKUL": ("Transito", "Subzona 2"),
    "TIXKOKOB": ("Transito", "Subzona 2"),
    "CACALCHEN": ("Transito", "Subzona 2"),
    # Transito - Subzona 3
    "DZILAM GONZALEZ": ("Transito", "Subzona 3"),
    "TEMAX": ("Transito", "Subzona 3"),
    "CANSANCAB": ("Transito", "Subzona 3"),  # por si acaso
    "CANSAHCAB": ("Transito", "Subzona 3"),
    "DZONCAUICH": ("Transito", "Subzona 3"),
    "SUMA": ("Transito", "Subzona 3"),
    "TEPAKAN": ("Transito", "Subzona 3"),
    "TEYA": ("Transito", "Subzona 3"),
    "TEKAL DE VENEGAS": ("Transito", "Subzona 3"),
    "TEKANTO": ("Transito", "Subzona 3"),
    "BOKOBA": ("Transito", "Subzona 3"),
    "IZAMAL": ("Transito", "Subzona 3"),
    # Transito - Subzona 4
    "TETIZ": ("Transito", "Subzona 4"),
    "SAMAHIL": ("Transito", "Subzona 4"),
    "KINCHIL": ("Transito", "Subzona 4"),
    "CHOCHOLA": ("Transito", "Subzona 4"),
    "ABALA": ("Transito", "Subzona 4"),
    # Descarga
    "IXIL": ("Descarga", "Subzona 1"),
    "PROGRESO": ("Descarga", "Subzona 1"),
    "SINANCHE": ("Descarga", "Subzona 2"),
    "TELCHAC PUERTO": ("Descarga", "Subzona 2"),
    "DZEMUL": ("Descarga", "Subzona 2"),
    "DZILAM DE BRAVO": ("Descarga", "Subzona 3"),
    "DZIDZANTUN": ("Descarga", "Subzona 3"),
    "YOBAIN": ("Descarga", "Subzona 3"),
    "HUNUCMA": ("Descarga", "Subzona 4"),
    "CELESTUN": ("Descarga", "Subzona 4"),
}


def norm_text(val: str) -> str:
    """Normaliza texto a mayusculas ASCII sin acentos ni espacios extra."""
    if val is None:
        return ""
    s = unicodedata.normalize("NFKD", str(val).upper())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.split()).strip()


def classify_usv_macro(descripcio: str) -> str:
    """Mapea categorias de Uso del Suelo y Vegetacion Serie VII a 4 macro-clases."""
    d = norm_text(descripcio)
    if "ASENTAMIENTOS HUMANOS" in d or "URBANO" in d:
        return "URBANO"
    if any(
        k in d
        for k in [
            "AGRICULTURA",
            "PASTIZAL CULTIVADO",
            "PASTIZAL INDUCIDO",
            "BOSQUE CULTIVADO",
            "PALMAR INDUCIDO",
            "ACUICOLA",
        ]
    ):
        return "AGROPECUARIO"
    if "CUERPO DE AGUA" in d:
        return "CUERPO_AGUA"
    if any(
        k in d
        for k in [
            "SELVA",
            "VEGETACION",
            "MANGLAR",
            "TULAR",
            "SABANA",
            "PASTIZAL HALOFILO",
            "DESPROVISTO DE VEGETACION",
            "SIN VEGETACION APARENTE",
        ]
    ):
        return "NATURAL"
    return "OTROS"

