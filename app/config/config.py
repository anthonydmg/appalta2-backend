import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi_mail import ConnectionConfig

# Carga las variables del archivo .env
load_dotenv()

logger = logging.getLogger(__name__)

# Información básica de la aplicación
APP_NAME = os.getenv("APP_NAME", "Appalta2")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# Base de datos
DATABASE_URL = os.getenv("DATABASE_URL")
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 10))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", 20))

# JWT. Sin SECRET_KEY en el entorno se usa la clave histórica para no invalidar
# las sesiones ya emitidas, pero en producción debe definirse.
SECRET_KEY = os.getenv("SECRET_KEY") or "super-secret-key"
if not os.getenv("SECRET_KEY"):
    logger.warning("SECRET_KEY no está definida: se usa la clave por defecto (inseguro en producción).")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

# Estaciones
MAX_DRIFT_SECONDS = 300  # 5 minutos de tolerancia en el timestamp firmado
ONLINE_TIMEOUT = 24 * 60 * 60  # una estación sin datos en 24 h se muestra offline

# Configuración de correo
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_FROM = os.getenv("MAIL_FROM", MAIL_USERNAME)
MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_STARTTLS = os.getenv("MAIL_STARTTLS", "True") == "True"
MAIL_SSL_TLS = os.getenv("MAIL_SSL_TLS", "False") == "True"
USE_CREDENTIALS = os.getenv("USE_CREDENTIALS", "True") == "True"

# Configuración para FastAPI-Mail
mail_conf = ConnectionConfig(
    MAIL_USERNAME=MAIL_USERNAME,
    MAIL_PASSWORD=MAIL_PASSWORD,
    MAIL_FROM=MAIL_FROM,
    MAIL_PORT=MAIL_PORT,
    MAIL_SERVER=MAIL_SERVER,
    MAIL_STARTTLS=MAIL_STARTTLS,
    MAIL_SSL_TLS=MAIL_SSL_TLS,
    USE_CREDENTIALS=USE_CREDENTIALS,
)
