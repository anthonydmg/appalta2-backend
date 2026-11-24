
from app.database.connection import get_db
from app.services.ollama_client import OllamaClient
from app.services.agroclimatic_reasoning import (
    AgroclimaticReasoningService,
)

from app.services.agroclimatic_prompt_builder_v2 import (
    AgroclimaticPromptBuilderV2,
)

from app.services.agronomic_context_builder import (
    AgronomicContextBuilder,
)

from app.services.climate_analysis import (
    ClimateAnalysisService,
)

from app.services.climate_context_builder import (
    ClimateContextBuilder,
)

from app.services.scientific_knowledge import (
    ScientificKnowledgeService,
)

from app.schemas.agronomic_context import (
    VisionDiagnosisInput,
)


def test_agroclimatic_stream():

    db_generator = get_db()
    db = next(db_generator)
    

    try:
        # 1. Crear diagnóstico de prueba.
        diagnosis = VisionDiagnosisInput(
            station_code="EST002-PALTAS",
            detected_pests=[
                {
                    "scientific_name": "Fiorinia fioriniae",
                    "common_name": "Queresa",
                    "confidence": 0.94,
                    "affected_leaf_side": "underside",
                }
            ],
            detected_damages=[
                {
                    "damage_name": "Presencia de queresas",
                    "description": (
                        "Presencia de individuos "
                        "en el envés de la hoja"
                    ),
                }
            ],
        )

        # 2. Construir contexto agronómico.
        climate_analysis_service = ClimateAnalysisService(db)

        climate_context_builder = ClimateContextBuilder()

        scientific_knowledge_service = ScientificKnowledgeService(db)

        agronomic_context_builder = AgronomicContextBuilder(
            climate_analysis_service=climate_analysis_service,
            climate_context_builder=climate_context_builder,
            scientific_knowledge_service=scientific_knowledge_service,
        )

        agronomic_context = agronomic_context_builder.build(
            diagnosis=diagnosis,
            evidence_limit=100,
        )

        print("\nCONTEXTO AGRONÓMICO CONSTRUIDO")

        # 3. Crear servicio de razonamiento.
        ollama_client = OllamaClient()

        prompt_builder = AgroclimaticPromptBuilderV2(
            expected_evidence_count=20
        )

        reasoning_service = AgroclimaticReasoningService(
            ollama_client=ollama_client,
            prompt_builder=prompt_builder,
        )

        # 4. Ejecutar streaming.
        print("\n===== INICIO DEL STREAMING =====\n")

        for event in reasoning_service.analyze_stream(
            agronomic_context=agronomic_context,
        ):

            if event["event"] == "section":

                print(
                    f"\n[SECCIÓN COMPLETADA] "
                    f"{event['section']}"
                )

                print(event["data"])

            elif event["event"] == "report_completed":

                print("\n===== INFORME FINAL COMPLETADO =====")

                print("\nMODELO:")
                print(event["model"])

                print("\nMÉTRICAS:")
                print(event["metrics"])

                print("\nINFORME AGROCLIMÁTICO:")
                print(
                    event["analysis"].model_dump_json(
                        indent=2,
                        ensure_ascii=False,
                    )
                )

        print("\n===== PRUEBA FINALIZADA =====")

    finally:
        db.close()


if __name__ == "__main__":
    test_agroclimatic_stream()
