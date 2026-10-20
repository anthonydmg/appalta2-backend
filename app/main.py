import logging

from fastapi import FastAPI

from app.assistant import assistant_router
from app.config import settings
from app.routes.measurements import router as measurements_router
from app.routes.stations import router as stations_router
from app.routes.user import router as user_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

API_PREFIX = "/api/v1"
VERSION = "1.0.0"

# Swagger solo si está habilitado (en producción, por defecto no: API_DOCS_ENABLED)
app = FastAPI(
    title="Backend Appalta2",
    version=VERSION,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

app.include_router(user_router, prefix=API_PREFIX, tags=["Users"])
app.include_router(measurements_router, prefix=API_PREFIX, tags=["Measurements"])
app.include_router(stations_router, prefix=API_PREFIX, tags=["Stations"])
# Módulo Asistente IA (chat por estación). Autocontenido en app/assistant/.
app.include_router(assistant_router, prefix=API_PREFIX)
