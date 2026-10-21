"""Constantes de la aplicación (no dependen del entorno)."""

from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# Estaciones
MAX_DRIFT_SECONDS = 300  # 5 minutos de tolerancia en el timestamp firmado
ONLINE_TIMEOUT = 24 * 60 * 60  # una estación sin datos en 24 h se muestra offline
