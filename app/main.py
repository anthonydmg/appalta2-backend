import logging

from fastapi import FastAPI

from app.assistant import assistant_router
from app.config import settings
from app.routes.measurements import router as measurements_router
from app.routes.stations import router as stations_router
from app.routes.user import router as user_router
from app.routes.diagnosis import router as diagnosis_router
from app.routes.scientific_knowledge import router as scientific_knowledge_router
from app.routes.maps import router as maps_router
from app.routes.crop_fields import router as crop_fields_router
from app.routes.field_mappings import router as field_mappings_router

from fastapi.middleware.cors import CORSMiddleware
from app.routes.agroclimatic_reports import (
    router as agroclimatic_reports_router
)

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router, prefix=API_PREFIX, tags=["Users"])
app.include_router(measurements_router, prefix=API_PREFIX, tags=["Measurements"])
app.include_router(stations_router, prefix=API_PREFIX, tags=["Stations"])
# Módulo Asistente IA (chat por estación). Autocontenido en app/assistant/.
app.include_router(assistant_router, prefix=API_PREFIX)
app.include_router(diagnosis_router, prefix=API_PREFIX)
app.include_router(scientific_knowledge_router, prefix=API_PREFIX)
app.include_router(
    agroclimatic_reports_router,
    prefix=API_PREFIX,
)
app.include_router(maps_router, prefix=API_PREFIX)
app.include_router(crop_fields_router, prefix=API_PREFIX)

app.include_router(field_mappings_router, prefix=API_PREFIX)