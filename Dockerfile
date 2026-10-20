# syntax=docker/dockerfile:1
# Backend Appalta2 (API + asistente IA) para producción. Ver DEPLOY.md y SERVICES.md.
#
#   docker compose --env-file .env.production up -d --build
#
# Dos etapas: las dependencias se instalan en un venv aparte y a la imagen final solo
# llega ese venv + el código (sin pip cache ni herramientas de compilación).

# Misma versión de Python con la que se probó el proyecto
ARG PYTHON_IMAGE=python:3.11.17-slim-bookworm

# ---------------------------------------------------------------------
# 1. Dependencias
# ---------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS deps

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

# Se reutiliza la capa mientras requirements.txt no cambie
COPY requirements.txt .
RUN pip install -r requirements.txt

# ---------------------------------------------------------------------
# 2. Imagen final
# ---------------------------------------------------------------------
FROM ${PYTHON_IMAGE}

ARG APP_VERSION=1.0.0
LABEL org.opencontainers.image.title="appalta2-backend" \
      org.opencontainers.image.description="API de Appalta2: usuarios, estaciones IoT y asistente IA" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.vendor="INICTEL-UNI" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/pdsiia-inictel-uni/appalta2-backend"

# Sin .pyc (el sistema de archivos del contenedor es de solo lectura) y logs sin buffer
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    APP_VERSION=${APP_VERSION}

# Usuario sin privilegios ni shell de login
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin appuser

COPY --from=deps /opt/venv /opt/venv

WORKDIR /app

# Código, scripts (migraciones, check_env, evaluación del asistente) y migraciones SQL.
# Quedan de root: el proceso (appuser) puede leerlos pero no modificarlos.
COPY app/ app/
COPY scripts/ scripts/
COPY sql/ sql/
COPY --chmod=755 docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
# Por si el archivo llegó con fin de línea de Windows (CRLF)
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh

USER appuser

EXPOSE 8000

# Salud del proceso (no depende de la BD ni del modelo; eso lo informa /api/v1/assistant/health)
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/', timeout=4)" || exit 1

# Aplica las migraciones pendientes (MIGRATE_ON_START=true) y luego ejecuta CMD
ENTRYPOINT ["docker-entrypoint.sh"]

# Un solo proceso: el historial del chat, los clientes SSE y el límite de intentos viven en
# memoria (ver SERVICES.md). --proxy-headers: detrás del proxy HTTPS de producción.
# --timeout-graceful-shutdown: los streams SSE no terminan solos; al detener se cierran a los 15 s.
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "1", \
     "--proxy-headers", "--forwarded-allow-ips", "*", \
     "--timeout-graceful-shutdown", "15", "--no-server-header"]
