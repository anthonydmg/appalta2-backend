
# ============================================================
# Imagen base
# ============================================================
ARG PYTHON_IMAGE=python:3.11.17-slim-bookworm

# ============================================================
# 1. Etapa de dependencias
# ============================================================
FROM ${PYTHON_IMAGE} AS deps

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Crear entorno virtual e instalar dependencias
RUN python -m venv /opt/venv

COPY requirements.txt .
RUN /opt/venv/bin/pip install -r requirements.txt

# ============================================================
# 2. Imagen final
# ============================================================
FROM ${PYTHON_IMAGE}

ARG APP_VERSION=1.0.0

LABEL org.opencontainers.image.title="appalta2-backend" \
      org.opencontainers.image.description="API de Appalta2: usuarios, estaciones Agrometeorologicas y asistente IA" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.vendor="INICTEL-UNI" \
      org.opencontainers.image.source="https://github.com/pdsiia-inictel-uni/appalta2-backend"

# Configuración de Python y aplicación
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_VERSION="${APP_VERSION}"

# Crear usuario sin privilegios
RUN useradd --system \
    --uid 10001 \
    --no-create-home \
    --shell /usr/sbin/nologin \
    appuser

# Copiar entorno virtual de la etapa anterior
COPY --from=deps /opt/venv /opt/venv

WORKDIR /app

# Copiar código, scripts y migraciones
COPY app/ ./app/
COPY scripts/ ./scripts/

# Ejecutar la API con un usuario sin privilegios
USER appuser

EXPOSE 8000

# Comprobar que la API responde correctamente
HEALTHCHECK --interval=30s \
            --timeout=5s \
            --start-period=30s \
            --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/', timeout=4)" || exit 1

# Ejecutar entrypoint antes de iniciar FastAPI
ENTRYPOINT ["docker-entrypoint.sh"]

# Iniciar Uvicorn
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*", \
     "--timeout-graceful-shutdown", "15", \
     "--no-server-header"]
