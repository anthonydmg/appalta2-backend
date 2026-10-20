"""Lectura de variables de entorno (app/config/settings.py), sin depender del .env local."""

import pytest
from pydantic import ValidationError

from app.config.settings import Settings

STRONG_SECRET = "x" * 48
BASE = {"DATABASE_URL": "postgresql+psycopg2://u:p@localhost/db"}


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch):
    """Solo cuentan las variables que define cada test (ni el .env ni el entorno del equipo)."""
    import os

    for name in list(os.environ):
        if name.startswith(("APP_", "PUBLIC_", "DB_", "JWT_", "MAIL_", "BACKEND_URL", "SECRET_KEY", "USE_CREDENTIALS")):
            monkeypatch.delenv(name, raising=False)
    for name, value in BASE.items():
        monkeypatch.setenv(name, value)


def load(**env) -> Settings:
    import os

    for name, value in env.items():
        os.environ[name] = value
    try:
        return Settings(_env_file=None)
    finally:
        for name in env:
            os.environ.pop(name, None)


def test_defaults_for_local_development():
    s = load()
    assert s.app_env == "development" and not s.is_production
    assert s.public_api_url == "http://localhost:8000/api"
    assert s.mail_use_credentials is True and s.mail_ssl_tls is False


def test_legacy_variable_names_are_still_accepted():
    s = load(BACKEND_URL="https://x.pe/api/palta/", SECRET_KEY=STRONG_SECRET, USE_CREDENTIALS="False")
    assert s.public_api_url == "https://x.pe/api/palta"  # sin "/" final
    assert s.jwt_secret_key.get_secret_value() == STRONG_SECRET
    assert s.mail_use_credentials is False


def test_new_name_wins_over_legacy_name():
    s = load(PUBLIC_API_URL="https://nueva.pe/api", BACKEND_URL="https://vieja.pe/api")
    assert s.public_api_url == "https://nueva.pe/api"


@pytest.mark.parametrize("raw, expected", [("true", True), ("True", True), ("1", True), ("false", False), ("0", False)])
def test_booleans_accept_usual_spellings(raw, expected):
    assert load(MAIL_STARTTLS=raw).mail_starttls is expected


@pytest.mark.parametrize("secret", [None, "", "corta", "super-secret-key"])
def test_production_refuses_missing_or_weak_jwt_secret(secret):
    env = {"APP_ENV": "production"} | ({"JWT_SECRET_KEY": secret} if secret is not None else {})
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        load(**env)


def test_production_with_strong_secret():
    assert load(APP_ENV="production", JWT_SECRET_KEY=STRONG_SECRET).is_production


def test_empty_secret_in_development_never_signs_with_empty_key():
    assert load(JWT_SECRET_KEY="").jwt_secret_key.get_secret_value() != ""


def test_mail_from_defaults_to_username_and_postgres_url_is_fixed():
    s = load(MAIL_USERNAME="a@b.pe", DATABASE_URL="postgres://u:p@h:5432/db")
    assert s.mail_from == "a@b.pe"
    assert s.database_url == "postgresql+psycopg2://u:p@h:5432/db"


def test_invalid_app_env_is_rejected():
    with pytest.raises(ValidationError):
        load(APP_ENV="staging")
