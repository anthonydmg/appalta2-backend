"""Verifica la base de datos de DATABASE_URL y, si no existe, la crea y ejecuta sql/*.sql.

Lo usa run.ps1 en lugar de psql: en Windows con Smart App Control (Control de aplicaciones)
psql.exe queda bloqueado, mientras que pg8000 es Python puro y siempre funciona.

Uso:  python -m scripts.setup_db [--database otro_nombre]
Código de salida 0 = lista para usar; 1 = error (el mensaje explica qué revisar).
"""

import argparse
import os
import sys
from pathlib import Path

import pg8000.native
from dotenv import load_dotenv
from sqlalchemy.engine import make_url

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def connect(url, database: str) -> pg8000.native.Connection:
    return pg8000.native.Connection(
        user=url.username, password=url.password, host=url.host or "localhost", port=url.port or 5432, database=database
    )


def main(database: str | None = None) -> int:
    load_dotenv()
    raw = os.getenv("DATABASE_URL")
    if not raw:
        print("ERROR: DATABASE_URL no está definida en .env.")
        return 1
    url = make_url(raw)
    name = database or url.database
    print(f"==> Verificando PostgreSQL en {url.host}:{url.port or 5432}")
    try:
        admin = connect(url, "postgres")
    except Exception as e:  # conexión, usuario o contraseña
        print(f"ERROR: No se pudo conectar a PostgreSQL ({e}). Revisa el servicio y el usuario/clave de DATABASE_URL.")
        return 1
    try:
        if admin.run("SELECT 1 FROM pg_database WHERE datname = :name", name=name):
            print(f"    Base de datos '{name}' ya existe.")
            return 0
        print(f"==> Creando base de datos '{name}'")
        admin.run(f"CREATE DATABASE {pg8000.native.identifier(name)} ENCODING 'UTF8' TEMPLATE template0")
    finally:
        admin.close()

    con = connect(url, name)
    try:
        for script in sorted(SQL_DIR.glob("*.sql")):
            print(f"==> Ejecutando {script.name}")
            # Cada script en una transacción: si falla, no queda a medias.
            con.execute_simple("BEGIN")
            try:
                con.execute_simple(script.read_text(encoding="utf-8"))
                con.execute_simple("COMMIT")
            except Exception as e:
                con.execute_simple("ROLLBACK")
                print(f"ERROR: Falló el script {script.name}: {e}")
                return 1
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--database", default=None, help="nombre de la base (por defecto, el de DATABASE_URL)")
    sys.exit(main(parser.parse_args().database))
