
import json
import logging

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db

from app.schemas.agronomic_context import VisionDiagnosisInput
from app.schemas.agroclimatic_report import AgroclimaticReport

from app.services.climate_analysis import ClimateAnalysisService
from app.services.climate_context_builder import ClimateContextBuilder
from app.services.scientific_knowledge import ScientificKnowledgeService
from app.services.agronomic_context_builder import AgronomicContextBuilder

from app.services.agroclimatic_prompt_builder_v2 import (
    AgroclimaticPromptBuilderV2
)

from app.services.ollama_client import OllamaClient

from app.services.agroclimatic_reasoning import (
    AgroclimaticReasoningService
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/agroclimatic-reports",
    tags=["Agroclimatic Reports"]
)


def build_agronomic_context(
    diagnosis: VisionDiagnosisInput,
    db: Session
):
    """
    Construye el contexto agronómico a partir del diagnóstico,
    las mediciones climáticas y la evidencia científica.
    """

    # 1. Servicios de clima y conocimiento científico.
    climate_service = ClimateAnalysisService(db)

    climate_context_builder = ClimateContextBuilder()

    scientific_service = ScientificKnowledgeService(db)

    # 2. Constructor del contexto agronómico.
    agronomic_builder = AgronomicContextBuilder(
        climate_analysis_service=climate_service,
        climate_context_builder=climate_context_builder,
        scientific_knowledge_service=scientific_service
    )

    # 3. Fecha de referencia.
    reference_time = datetime(
        2026, 11, 6,
        tzinfo=timezone.utc
    )

    # 4. Construir contexto.
    return agronomic_builder.build(
        diagnosis=diagnosis,
        evidence_limit=100,
        reference_time=reference_time
    )


def build_reasoning_service():
    """
    Construye el servicio de razonamiento agroclimático.
    """

    prompt_builder = AgroclimaticPromptBuilderV2()

    ollama_client = OllamaClient()

    return AgroclimaticReasoningService(
        ollama_client=ollama_client,
        prompt_builder=prompt_builder
    )


@router.post(
    "/generate",
    response_model=AgroclimaticReport
)
def generate_agroclimatic_report(
    diagnosis: VisionDiagnosisInput,
    db: Session = Depends(get_db)
):
    """
    Genera el informe agroclimático completo en JSON.
    """

    try:
        # 1. Construir contexto agronómico.
        agronomic_context = build_agronomic_context(
            diagnosis=diagnosis,
            db=db
        )

        # 2. Crear servicio de razonamiento.
        reasoning_service = build_reasoning_service()

        # 3. Generar informe.
        result = reasoning_service.analyze(
            agronomic_context=agronomic_context
        )

        # 4. Devolver informe.
        return result["analysis"]

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Error generando informe agroclimático"
        )

        raise HTTPException(
            status_code=500,
            detail="No fue posible generar el informe agroclimático."
        ) from exc


@router.post(
    "/generate/stream"
)
def generate_agroclimatic_report_stream(
    diagnosis: VisionDiagnosisInput,
    db: Session = Depends(get_db)
):
    """
    Genera el informe agroclimático mediante Server-Sent Events.
    """

    try:
        # 1. Construir contexto agronómico antes del streaming.
        agronomic_context = build_agronomic_context(
            diagnosis=diagnosis,
            db=db
        )

        # 2. Crear servicio de razonamiento.
        reasoning_service = build_reasoning_service()

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Error preparando el streaming agroclimático"
        )

        raise HTTPException(
            status_code=500,
            detail="No fue posible preparar el informe agroclimático."
        ) from exc

    def event_generator():

        try:
            # 3. Ejecutar generación progresiva.
            for event in reasoning_service.analyze_stream(
                agronomic_context=agronomic_context
            ):

                event_name = event["event"]

                # Convertir modelos Pydantic y otros objetos
                # a estructuras serializables en JSON.
                if event_name == "report_completed":
                    event_data = {
                        **event,
                        "analysis": event["analysis"].model_dump(
                            mode="json"
                        )
                    }
                else:
                    event_data = event

                # 4. Construir evento SSE.
                yield (
                    f"event: {event_name}\n"
                    f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                )

        except Exception:
            logger.exception(
                "Error durante el streaming del informe agroclimático"
            )

            error_data = {
                "message": (
                    "Ocurrió un error durante la generación "
                    "del informe agroclimático."
                )
            }

            yield (
                "event: error\n"
                f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            )

    # 5. Devolver respuesta SSE.
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
