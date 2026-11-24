
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.scientific_knowledge import (
    ScientificEvidenceQuery,
    ScientificEvidenceSearchResponse,
)
from app.services.scientific_knowledge import (
    ScientificKnowledgeService,
)

from app.services.scientific_assistant import (
    ScientificAssistantService
)

from app.schemas.scientific_knowledge import (
    ScientificQuestionRequest,
    ScientificQuestionResponse
)

import httpx

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/knowledge",
    tags=["Scientific Knowledge"]
)


@router.get(
    "/scientific-temporal-patterns",
    summary="Buscar patrones temporales científicos",
    description=(
        "Recupera patrones estacionales y periodos de actividad "
        "biológica según especie, mes y ubicación del estudio."
    )
)
def search_scientific_temporal_patterns(
    scientific_name: str | None = Query(default=None),
    month: int | None = Query(default=None, ge=1, le=12),
    location: str | None = Query(default=None),
    validation_status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    try:
        service = ScientificKnowledgeService(db)

        return service.search_temporal_patterns(
            scientific_name=scientific_name,
            month=month,
            location=location,
            validation_status=validation_status,
            limit=limit
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc)
        )

    except SQLAlchemyError:
        logger.exception(
            "Error consultando patrones temporales científicos"
        )

        raise HTTPException(
            status_code=500,
            detail="Error al consultar los patrones temporales."
        )



@router.post(
    "/ask",
    response_model=ScientificQuestionResponse,
    summary="Consultar asistente científico agronómico"
)
def ask_scientific_assistant(
    request: ScientificQuestionRequest,
    db: Session = Depends(get_db)
):

    try:

        assistant = ScientificAssistantService(db)

        response = assistant.answer(
            question=request.question,
            scientific_name=request.scientific_name,
            climate_variable=request.climate_variable,
            biological_response=request.biological_response,
            location=request.location,
            study_type=request.study_type,
            validation_status=request.validation_status,
            limit=request.limit
        )

        return response

    except httpx.HTTPError:

        logger.exception(
            "Error comunicándose con Ollama"
        )

        raise HTTPException(
            status_code=503,
            detail="No fue posible comunicarse con el servidor Ollama."
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=422,
            detail=str(exc)
        )

    except Exception:

        logger.exception(
            "Error procesando la consulta científica"
        )

        raise HTTPException(
            status_code=500,
            detail="Error procesando la consulta científica."
        )


@router.get(
    "/scientific-evidence",
    response_model=ScientificEvidenceSearchResponse,
    summary="Buscar evidencia científica",
    description=(
        "Recupera evidencia científica mediante filtros "
        "taxonómicos, climáticos, biológicos y geográficos."
    )
)
def search_scientific_evidence(
    scientific_name: str | None = Query(default=None),
    climate_variable: str | None = Query(default=None),
    biological_response: str | None = Query(default=None),
    location: str | None = Query(default=None),
    study_type: str | None = Query(default=None),
    validation_status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    try:
        service = ScientificKnowledgeService(db)

        response = service.search_evidence(
            scientific_name=scientific_name,
            climate_variable=climate_variable,
            biological_response=biological_response,
            location=location,
            study_type=study_type,
            validation_status=validation_status,
            limit=limit
        )

        return response

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc)
        )

    except SQLAlchemyError:
        logger.exception(
            "Error consultando la evidencia científica"
        )

        raise HTTPException(
            status_code=500,
            detail="Error al consultar la base de conocimiento científica."
        )
