"""Verifica un archivo de variables de entorno sin mostrar secretos.

Valida con las mismas reglas que la API (app/config/environment.py) y, si se pide, prueba
la conexión a PostgreSQL y al servidor SMTP.

Uso:
  python -m scripts.check_env                       # revisa .env
  python -m scripts.check_env .env.production       # revisa el de producción
  python -m scripts.check_env .env --connect        # además prueba BD y SMTP
  docker compose --env-file .env.production run --rm backend python -m scripts.check_env -   # en el contenedor

Código de salida 0 = listo; 1 = hay errores que impiden arrancar.
"""

import argparse
import smtplib
import sys
from pathlib import Path

from pydantic import SecretStr, ValidationError

from app.config.environment import ROOT_DIR, Settings

SECRETS = {"database_url", "jwt_secret_key", "mail_password"}


def _mask(name: str, value) -> str:
    if isinstance(value, SecretStr) or name in SECRETS:
        raw = value.get_secret_value() if isinstance(value, SecretStr) else str(value)
        if name == "database_url" and "@" in raw:  # muestra servidor y base, oculta usuario y clave
            return "***@" + raw.split("@", 1)[1]
        return f"*** ({len(raw)} caracteres)" if raw else "(vacío)"
    return str(value)


def _warnings(settings: Settings) -> list[str]:
    """Valores que dejan arrancar la API pero rompen alguna función en uso real."""
    found = []
    if settings.mail_username in ("", "correo@gmail.com"):
        found.append("MAIL_USERNAME es el ejemplo de la plantilla: no se enviarán correos de verificación "
                     "(sin verificar, los usuarios no pueden iniciar sesión).")
    app_password = settings.mail_password.get_secret_value().replace(" ", "")
    if "gmail" in settings.mail_server and settings.mail_use_credentials and len(app_password) != 16:
        found.append(f"MAIL_PASSWORD tiene {len(app_password)} caracteres; la contraseña de aplicación de Gmail tiene 16.")
    if settings.is_production and not settings.public_api_url.startswith("https://"):
        found.append(f"PUBLIC_API_URL={settings.public_api_url}: los enlaces de los correos no serán accesibles "
                     "para los usuarios (en producción debe ser la URL pública https://).")
    return found


def _check_database(settings: Settings) -> str:
    from sqlalchemy import create_engine, text

    engine = create_engine(settings.database_url, pool_pre_ping=True)
    with engine.connect() as conn:
        version = conn.execute(text("SHOW server_version")).scalar()
    engine.dispose()
    return f"OK (PostgreSQL {version})"


def _check_smtp(settings: Settings) -> str:
    smtp_cls = smtplib.SMTP_SSL if settings.mail_ssl_tls else smtplib.SMTP
    with smtp_cls(settings.mail_server, settings.mail_port, timeout=10) as smtp:
        if settings.mail_starttls:
            smtp.starttls()
        if settings.mail_use_credentials:
            smtp.login(settings.mail_username, settings.mail_password.get_secret_value())
    return "OK (autenticado)" if settings.mail_use_credentials else "OK"


def main(env_file: str, connect: bool) -> int:
    if env_file == "-":
        # Dentro del contenedor: Docker Compose ya inyectó .env.production como variables
        path, label = None, "variables de entorno del proceso"
    else:
        path = Path(env_file)
        if not path.is_absolute():
            path = ROOT_DIR / path
        if not path.exists():
            print(f"ERROR: no existe {path}. Créalo con:  cp .env.example {path.name}")
            return 1
        label = path.name

    print(f"==> {label}")
    try:
        settings = Settings(_env_file=path)
    except ValidationError as e:
        print("ERROR: la API no arrancaría con esta configuración:")
        for err in e.errors():
            field = ".".join(str(p) for p in err["loc"]) or "configuración"
            print(f"  - {field}: {err['msg'].removeprefix('Value error, ')}")
        return 1

    for name, value in settings:
        print(f"  {name.upper():<34} {'(por defecto)' if value is None else _mask(name, value)}")
    print(f"  {'(Swagger /docs)':<34} {'habilitado' if settings.docs_enabled else 'cerrado'}")

    warnings = _warnings(settings)
    for warning in warnings:
        print(f"AVISO: {warning}")

    if connect:
        for label, check in (("PostgreSQL", _check_database), ("SMTP", _check_smtp)):
            try:
                print(f"==> {label}: {check(settings)}")
            except Exception as e:
                print(f"ERROR {label}: {e}")
                return 1
    print("==> Configuración válida." + (f" Revisa {len(warnings)} aviso(s)." if warnings else ""))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("env_file", nargs="?", default=".env",
                        help="archivo a revisar (por defecto .env; '-' = solo variables del entorno)")
    parser.add_argument("--connect", action="store_true", help="prueba la conexión a PostgreSQL y SMTP")
    args = parser.parse_args()
    sys.exit(main(args.env_file, args.connect))
