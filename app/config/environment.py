"""Configuración del backend leída de variables de entorno (o del archivo .env en desarrollo).

Archivos: `.env` (desarrollo), `.env.production` (Docker) y su plantilla única `.env.example`.
Prioridad: variables del sistema/contenedor > archivo .env > valores por defecto de esta clase.
"""

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import dotenv_values
from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[2]
# Ruta absoluta: el .env se encuentra aunque uvicorn, pytest o los scripts se lancen desde otra carpeta
ENV_FILE = ROOT_DIR / ".env"

_INSECURE_JWT_SECRET = "super-secret-key"  # clave histórica; solo se tolera en desarrollo
PLACEHOLDER = "REEMPLAZAR"  # marca de los valores de .env.example que hay que completar

# Nombres anteriores -> nombre actual. Se siguen aceptando para no romper servidores ya configurados.
LEGACY_ENV_NAMES = {
    "BACKEND_URL": "PUBLIC_API_URL",
    "SECRET_KEY": "JWT_SECRET_KEY",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
    "REFRESH_TOKEN_EXPIRE_DAYS": "JWT_REFRESH_TOKEN_EXPIRE_DAYS",
    "USE_CREDENTIALS": "MAIL_USE_CREDENTIALS",
}


def _env(name: str) -> AliasChoices:
    """Nombre actual de la variable y, si existe, su nombre anterior."""
    legacy = [old for old, new in LEGACY_ENV_NAMES.items() if new == name]
    return AliasChoices(name, *legacy)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    # --- Aplicación ---
    app_env: Literal["development", "production"] = Field("development", validation_alias=_env("APP_ENV"))
    # URL pública del API sin "/v1" (con ella se arman los enlaces de los correos)
    public_api_url: str = Field("http://localhost:8000/api", validation_alias=_env("PUBLIC_API_URL"))
    # Swagger (/docs) y OpenAPI: por defecto abiertos en desarrollo y cerrados en producción
    api_docs_enabled: bool | None = Field(None, validation_alias=_env("API_DOCS_ENABLED"))

    # --- Base de datos ---
    database_url: str = Field(validation_alias=_env("DATABASE_URL"))
    db_pool_size: int = Field(10, ge=1, validation_alias=_env("DB_POOL_SIZE"))
    db_max_overflow: int = Field(20, ge=0, validation_alias=_env("DB_MAX_OVERFLOW"))

    # --- Autenticación (JWT) ---
    jwt_secret_key: SecretStr = Field(SecretStr(_INSECURE_JWT_SECRET), validation_alias=_env("JWT_SECRET_KEY"))
    jwt_access_token_expire_minutes: int = Field(30, ge=1, validation_alias=_env("JWT_ACCESS_TOKEN_EXPIRE_MINUTES"))
    jwt_refresh_token_expire_days: int = Field(7, ge=1, validation_alias=_env("JWT_REFRESH_TOKEN_EXPIRE_DAYS"))

    # --- Correo (SMTP) ---
    mail_server: str = Field("smtp.gmail.com", validation_alias=_env("MAIL_SERVER"))
    mail_port: int = Field(587, validation_alias=_env("MAIL_PORT"))
    mail_username: str = Field("", validation_alias=_env("MAIL_USERNAME"))
    mail_password: SecretStr = Field(SecretStr(""), validation_alias=_env("MAIL_PASSWORD"))
    mail_from: str = Field("", validation_alias=_env("MAIL_FROM"))  # vacío = MAIL_USERNAME
    mail_starttls: bool = Field(True, validation_alias=_env("MAIL_STARTTLS"))
    mail_ssl_tls: bool = Field(False, validation_alias=_env("MAIL_SSL_TLS"))
    mail_use_credentials: bool = Field(True, validation_alias=_env("MAIL_USE_CREDENTIALS"))

    @field_validator("public_api_url")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("database_url")
    @classmethod
    def _sqlalchemy_driver(cls, value: str) -> str:
        # Algunos proveedores entregan "postgres://"; SQLAlchemy necesita "postgresql+psycopg2://"
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg2://", 1)
        return value

    @model_validator(mode="after")
    def _check_secrets(self):
        # Valores de la plantilla .env.example que no se reemplazaron
        placeholders = sorted(
            name.upper()
            for name, value in self
            if PLACEHOLDER in str(value.get_secret_value() if isinstance(value, SecretStr) else value)
        )
        if placeholders and (self.is_production or "DATABASE_URL" in placeholders):
            raise ValueError(f"Reemplaza los valores de la plantilla en: {', '.join(placeholders)}")
        if placeholders:
            logger.warning("Variables sin configurar (aún con el valor de la plantilla): %s", ", ".join(placeholders))
        if self.is_production and not self.public_api_url.startswith("https://"):
            logger.warning("PUBLIC_API_URL no usa https:// en producción: los enlaces de los correos apuntan a %s",
                           self.public_api_url)
        if not self.mail_from:
            self.mail_from = self.mail_username
        secret = self.jwt_secret_key.get_secret_value().strip()
        if not secret:  # "JWT_SECRET_KEY=" vacío en el .env equivale a no definirla
            secret = _INSECURE_JWT_SECRET
            self.jwt_secret_key = SecretStr(secret)
        if secret == _INSECURE_JWT_SECRET or len(secret) < 32:
            if self.is_production:
                raise ValueError("JWT_SECRET_KEY debe definirse en producción (32+ caracteres aleatorios).")
            logger.warning("JWT_SECRET_KEY no está definida o es débil: se acepta solo en desarrollo.")
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def docs_enabled(self) -> bool:
        return self.api_docs_enabled if self.api_docs_enabled is not None else not self.is_production


def _warn_legacy_names() -> None:
    defined = set(os.environ) | set(dotenv_values(ENV_FILE) if ENV_FILE.exists() else {})
    for old, new in LEGACY_ENV_NAMES.items():
        if old in defined and new not in defined:
            logger.warning("Variable de entorno %s está obsoleta: renómbrala a %s.", old, new)


@lru_cache
def get_settings() -> Settings:
    _warn_legacy_names()
    return Settings()
