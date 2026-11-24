
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from app.schemas.agronomic_context import (
    VisionDiagnosisInput,
    DetectedPest,
    DetectedDamage
)
from app.schemas.agroclimatic_report import AgroclimaticReport
from app.services.climate_analysis import ClimateAnalysisService
from app.services.climate_context_builder import ClimateContextBuilder
from app.services.scientific_knowledge import ScientificKnowledgeService
from app.services.agronomic_context_builder import AgronomicContextBuilder

from app.services.agroclimatic_prompt_builder_v2 import (
    AgroclimaticPromptBuilderV2
)

from app.services.ollama_client import OllamaClient
from app.services.prompt_token_budget import PromptTokenBudget

from app.services.agroclimatic_reasoning import (
    AgroclimaticReasoningService
)

from app.schemas.agroclimatic_reasoning import (
    AgroclimaticReasoningResponse
)

from app.database.connection import get_db


PRIORITY_CLIMATE_VARIABLES = {
    "ambient_temperature",
    "ambient_humidity",
}


def main():

    db_generator = get_db()
    db = next(db_generator)

    try:

        # ==================================================
        # 1. INICIALIZAR SERVICIOS
        # ==================================================

        climate_service = ClimateAnalysisService(db)

        climate_context_builder = ClimateContextBuilder()

        scientific_service = ScientificKnowledgeService(db)

        agronomic_builder = AgronomicContextBuilder(
            climate_analysis_service=climate_service,
            climate_context_builder=climate_context_builder,
            scientific_knowledge_service=scientific_service
        )

        prompt_builder = AgroclimaticPromptBuilderV2(
            expected_evidence_count=20
        )

        ollama_client = OllamaClient()

        reasoning_service = AgroclimaticReasoningService(
            ollama_client=ollama_client,
            prompt_builder=prompt_builder
        )

        # ==================================================
        # 2. DIAGNÓSTICO DE PRUEBA
        # ==================================================

        diagnosis = VisionDiagnosisInput(
            diagnosis_id=125,
            station_code="EST002-PALTAS",
            detected_pests=[
                DetectedPest(
                    scientific_name="Fiorinia fioriniae",
                    common_name="Queresa",
                    confidence=0.94,
                    affected_leaf_side="underside"
                )
            ],
            detected_damages=[
                DetectedDamage(
                    damage_name="Presencia de queresas",
                    description=(
                        "Presencia de individuos en el envés de la hoja"
                    )
                )
            ]
        )

        # ==================================================
        # 3. CONSTRUIR CONTEXTO AGRONÓMICO
        # ==================================================

        reference_time = datetime(
            2026, 11, 6,
            tzinfo=timezone.utc
        )

        agronomic_context = agronomic_builder.build(
            diagnosis=diagnosis,
            reference_time=reference_time,
            evidence_limit=100
        )

        print("\n===== CONTEXTO AGRONÓMICO GENERADO =====")

        print(
            "Diagnóstico:",
            agronomic_context["diagnosis"].keys()
        )

        # ==================================================
        # 4. COMPACTAR CONTEXTO
        # ==================================================

        compact_context = prompt_builder._compact_context(
            agronomic_context
        )

        climate = compact_context["climate"]

        print("\n===== VALIDACIÓN DE VARIABLES CLIMÁTICAS =====")

        for period in climate["periods"]:

            for sensor in period["sensors"]:
                print({
                    "sensor_code": sensor["code"],
                    "sensor_name": sensor["name"],
                    "unit": sensor["unit"],
                    "stats": sensor["stats"],
                })
                        
            codes = [
                sensor["code"]
                for sensor in period["sensors"]
            ]

            assert set(codes).issubset(
                PRIORITY_CLIMATE_VARIABLES
            )

            assert "ambient_temperature" in codes
            assert "ambient_humidity" in codes

            print(
                f"Periodo: {period['days']} días | "
                f"Sensores: {codes}"
            )

        # ==================================================
        # 5. VALIDACIÓN DE EVIDENCIAS
        # ==================================================

        print("\n===== VALIDACIÓN DE EVIDENCIAS =====")

        pests = compact_context["diagnosis"]["pests"]

        total_evidences = 0

        for pest_item in pests:

            pest_name = pest_item["pest"]["scientific_name"]

            evidence = pest_item["evidence"]

            evidence_count = len(evidence)

            total_evidences += evidence_count

            print(f"\nPlaga: {pest_name}")
            print(f"Evidencias: {evidence_count}")

            for item in evidence:

                print(
                    f"  {item['study']} - {item['code']}"
                )

        assert total_evidences == 20, (
            f"Se esperaban 20 evidencias, "
            f"se encontraron {total_evidences}"
        )

        assert len(pests) == 1

        pest = pests[0]

        evidence = pest["evidence"]

        assert pest["retrieval"]["returned_evidences"] == 20

        # Distribución por estudio

        distribution = Counter(
            item["study"]
            for item in evidence
        )

        assert distribution == {
            "F01": 5,
            "F02": 5,
            "F03": 5,
            "F05": 5
        }, f"Distribución inesperada: {distribution}"

        # Campos científicos obligatorios

        required_fields = [
            "code",
            "study",
            "finding",
            "conditions",
            "result",
            "limit",
            "validation"
        ]

        for item in evidence:

            for field in required_fields:

                assert field in item, (
                    f"Falta {field} en evidencia "
                    f"{item.get('code')}"
                )

        # Períodos climáticos

        periods = climate["periods"]

        assert {
            period["days"] for period in periods
        } == {7, 15, 30}

        for period in periods:
            assert len(period["sensors"]) == 2

        # Estados de validación

        statuses = {
            item["validation"]
            for item in evidence
        }

        assert statuses == {
            "EXTRACTED_PENDING_AGRONOMIC_VALIDATION"
        }

        print("\nDistribución:", dict(distribution))
        print("Total evidencias:", total_evidences)
        print("Estados:", statuses)

        # ==================================================
        # 6. CONSTRUIR PROMPT
        # ==================================================

        prompt = prompt_builder.build(
            agronomic_context
        )

        # Perfilado del prompt

        sections = prompt_builder.build_sections(
            agronomic_context
        )

        print("\n===== PERFILADO DEL PROMPT =====")

        for name, content in sections.items():

            print(
                f"{name:15} | "
                f"{len(content):8,} caracteres | "
                f"{len(content.split()):6,} palabras"
            )

        # ==================================================
        # 7. VALIDAR PRESUPUESTO DE TOKENS
        # ==================================================

        print("\n===== CONFIGURACIÓN DE OLLAMA =====")

        print("Modelo:", ollama_client.model)
        print("Contexto:", ollama_client.num_ctx)
        print("Tokens de salida:", ollama_client.num_predict)
        print("Temperatura:", ollama_client.temperature)

        token_budget = PromptTokenBudget(
            ollama_client=ollama_client,
            output_reserve=2048,
            safety_margin=512
        )

        token_result = token_budget.validate(prompt)

        print("\n===== PRESUPUESTO PRELIMINAR =====")

        for key, value in token_result.items():
            print(f"{key}: {value}")

        # ==================================================
        # 8. GUARDAR PROMPT Y CONTEXTO
        # ==================================================

        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)

        prompt_file = output_dir / "agroclimatic_prompt_preview.txt"

        with prompt_file.open("w", encoding="utf-8") as file:
            file.write(prompt)

        context_file = output_dir / "agroclimatic_compact_context.json"

        with context_file.open("w", encoding="utf-8") as file:
            json.dump(
                compact_context,
                file,
                ensure_ascii=False,
                indent=2,
                default=str
            )

        print("\nContexto y prompt guardados correctamente.")

        # ==================================================
        # 9. EJECUTAR RAZONAMIENTO CON GEMMA
        # ==================================================

        print("\n==========================================")
        print("       EJECUTANDO GEMMA 4 E2B")
        print("==========================================")

        result = reasoning_service.analyze(
            agronomic_context=agronomic_context
        )

        # Verificar finalización de generación

        if result.get("done") is not True:
            raise RuntimeError(
                "Ollama no confirmó la finalización de la generación."
            )

        if result.get("done_reason") == "length":
            raise RuntimeError(
                "Gemma alcanzó el límite de tokens de salida."
            )

        # Extraer métricas ANTES de utilizarlas

        metrics = result.get("metrics", {})

        print("\n===== MÉTRICAS DE GENERACIÓN =====")

        for key, value in metrics.items():
            print(f"{key}: {value}")

        # Validar presupuesto con los tokens reales

        actual_tokens = metrics.get("prompt_tokens")

        actual_budget = token_budget.validate_actual_tokens(
            actual_tokens
        )

        print("\n===== VALIDACIÓN REAL DE TOKENS =====")

        for key, value in actual_budget.items():
            print(f"{key}: {value}")

        if not actual_budget["fits"]:
            raise RuntimeError(
                "El prompt supera el presupuesto de entrada."
            )

        # ==================================================
        # 10. VALIDAR RESPUESTA CON PYDANTIC
        # ==================================================

        analysis = result["analysis"]

        assert isinstance(
            analysis,
            AgroclimaticReport
        ), (
            f"Se esperaba AgroclimaticReport, "
            f"se recibió: {type(analysis).__name__}"
        )

        print("\n===== VALIDACIÓN PYDANTIC =====")
        print("Respuesta validada correctamente.")


        # Verificar finalización de generación

        if result.get("done") is not True:
            raise RuntimeError(
                "Ollama no confirmó la finalización de la generación."
            )

        # Extraer métricas

        metrics = result["metrics"]

        print("\n===== MÉTRICAS DE GENERACIÓN =====")

        for key, value in metrics.items():
            print(f"{key}: {value}")

        # Verificar límite de generación

        if result.get("done_reason") == "length":
            raise RuntimeError(
                "Gemma alcanzó el límite de tokens de salida."
            )

        # ==================================================
        # 10. VALIDAR RESPUESTA CON PYDANTIC
        # ==================================================

        analysis = result["analysis"]

        assert isinstance(
            analysis,
             AgroclimaticReport
        ), (
            f"Se esperaba AgroclimaticReport, "
            f"se recibió: {type(analysis).__name__}"
        )

        print("\n===== VALIDACIÓN PYDANTIC =====")
        print("Respuesta validada correctamente.")

        # ==================================================
        # 11. MOSTRAR RESPUESTA
        # ==================================================

        print("\n===== CONDICIONES CLIMÁTICAS =====")

        for item in analysis.climate_conditions:
            print(item.model_dump())
    
        analysis_json = analysis.model_dump(
            mode="json",
            exclude_none=False
        )

        print(
            json.dumps(
                analysis_json,
                ensure_ascii=False,
                indent=2
            )
        )

        # ==================================================
        # 12. GUARDAR RESULTADO FINAL
        # ==================================================

        result_file = output_dir / (
            "agroclimatic_reasoning_result.json"
        )

        with result_file.open("w", encoding="utf-8") as file:

            json.dump(
                {
                    "model": result.get("model"),
                    "metrics": metrics,
                    "analysis": analysis_json
                },
                file,
                ensure_ascii=False,
                indent=2
            )

        print("\n===== RESULTADO FINAL =====")

        print("Modelo:", result.get("model"))
        print("Archivo:", result_file)
        print("Prompt tokens:", metrics.get("prompt_tokens"))
        print("Generated tokens:", metrics.get("generated_tokens"))

        print("\nPrueba finalizada correctamente.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
