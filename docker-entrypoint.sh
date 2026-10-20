#!/bin/sh
# Punto de entrada del contenedor backend.
#   MIGRATE_ON_START=true  -> aplica las migraciones pendientes de sql/ antes de iniciar la API.
#                             Si una falla, el contenedor no arranca (ver: docker compose logs backend).
#   Cualquier otro comando (p. ej. "python -m scripts.check_env -") se ejecuta tal cual.
set -e

if [ "$1" = "uvicorn" ] && [ "${MIGRATE_ON_START:-false}" = "true" ]; then
    python -m scripts.setup_db
fi

exec "$@"
