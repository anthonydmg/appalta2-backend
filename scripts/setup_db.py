"""Prepara la base de DATABASE_URL: la crea si no existe y aplica las migraciones pendientes de sql/.

Cada script de sql/ se aplica una sola vez, en orden, dentro de una transacción, y queda
registrado en la tabla schema_migrations. Sirve igual para una base nueva y para la de
producción ya existente:

  - Base nueva:     ejecuta todos los scripts (esquema, índices, datos iniciales y migraciones).
  - Base existente sin schema_migrations (creada antes de este script): marca como aplicados
    los scripts del esquema inicial (BASELINE) sin ejecutarlos y aplica solo los posteriores.

Usa pg8000 (Python puro): en Windows con Smart App Control psql.exe queda bloqueado.

Uso:
  python -m scripts.setup_db             # crea/migra (run.ps1 lo ejecuta al arrancar)
  python -m scripts.setup_db --check     # solo muestra las migraciones pendientes
  docker compose --env-file .env.production run --rm backend python -m scripts.setup_db

Código de salida 0 = base al día; 1 = error (el mensaje explica qué revisar); 2 = hay pendientes (--check).
"""

import argparse
import sys
from pathlib import Path

import pg8000.native
from pydantic import ValidationError
from sqlalchemy.engine import make_url

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"

# Esquema inicial (tablas + datos de ejemplo): en bases creadas antes del control de migraciones
# ya existe, así que se registra sin volver a ejecutarse.
BASELINE = (
    "001_schema.sql",
    "002_indexes.sql",
    "003_seed_sensors.sql",
    "004_seed_stations.sql",
    "005_seed_station_sensors.sql",
)


def connect(url, database: str) -> pg8000.native.Connection:
    return pg8000.native.Connection(
        user=url.username, password=url.password, host=url.host or "localhost", port=url.port or 5432,
        database=database, application_name="appalta2-migrations",
    )  # fmt: skip


def ensure_database(url, name: str) -> bool:
    """Crea la base si no existe (necesita permiso CREATEDB). Devuelve True si la creó."""
    admin = connect(url, "postgres")
    try:
        if admin.run("SELECT 1 FROM pg_database WHERE datname = :name", name=name):
            return False
        print(f"==> Creando base de datos '{name}'")
        admin.run(f"CREATE DATABASE {pg8000.native.identifier(name)} ENCODING 'UTF8' TEMPLATE template0")
        return True
    finally:
        admin.close()


def _sqlstate(error: Exception) -> str | None:
    detail = error.args[0] if error.args else None
    return detail.get("C") if isinstance(detail, dict) else None


def table_exists(con, table: str) -> bool:
    return bool(con.run("SELECT to_regclass(:t) IS NOT NULL", t=f"public.{table}")[0][0])


def applied_migrations(con) -> set[str]:
    if not table_exists(con, "schema_migrations"):
        con.run(
            "CREATE TABLE schema_migrations (filename TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        if table_exists(con, "stations"):
            print("==> Base existente: se registra el esquema inicial sin volver a ejecutarlo")
            for name in BASELINE:
                con.run("INSERT INTO schema_migrations (filename) VALUES (:f)", f=name)
    return {row[0] for row in con.run("SELECT filename FROM schema_migrations")}


def apply(con, script: Path) -> None:
    print(f"==> Aplicando {script.name}")
    con.execute_simple("BEGIN")
    try:
        con.execute_simple(script.read_text(encoding="utf-8"))
        con.run("INSERT INTO schema_migrations (filename) VALUES (:f)", f=script.name)
        con.execute_simple("COMMIT")
    except Exception:
        con.execute_simple("ROLLBACK")  # el script no queda a medias ni registrado
        raise


def main(database: str | None = None, check: bool = False) -> int:
    try:
        from app.config import settings  # misma lectura y validación del .env que la API
    except ValidationError as e:
        print(f"ERROR: configuración inválida (ver .env.example):\n{e}")
        return 1
    url = make_url(settings.database_url)
    name = database or url.database
    print(f"==> PostgreSQL {url.host}:{url.port or 5432} / base '{name}'")

    try:
        try:
            con = connect(url, name)
        except pg8000.native.DatabaseError as e:
            # SQLSTATE 3D000 = la base no existe (el texto del error depende del idioma del servidor)
            if _sqlstate(e) != "3D000" or check:
                raise
            ensure_database(url, name)
            con = connect(url, name)
    except Exception as e:  # servicio caído, usuario/clave, permisos
        print(f"ERROR: No se pudo conectar ({e}). Revisa el servicio y DATABASE_URL.")
        return 1

    try:
        if check and not table_exists(con, "schema_migrations"):
            done = set(BASELINE) if table_exists(con, "stations") else set()
        else:
            done = applied_migrations(con)
        pending = [s for s in sorted(SQL_DIR.glob("*.sql")) if s.name not in done]
        if not pending:
            print("    Base de datos al día.")
            return 0
        if check:
            print("    Pendientes: " + ", ".join(s.name for s in pending))
            return 2
        for script in pending:
            try:
                apply(con, script)
            except Exception as e:
                print(f"ERROR: Falló {script.name}: {e}")
                return 1
        print(f"    {len(pending)} migración(es) aplicada(s).")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--database", default=None, help="nombre de la base (por defecto, el de DATABASE_URL)")
    parser.add_argument("--check", action="store_true", help="solo lista las migraciones pendientes, sin aplicarlas")
    args = parser.parse_args()
    sys.exit(main(args.database, args.check))
