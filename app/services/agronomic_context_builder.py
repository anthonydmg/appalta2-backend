
from datetime import datetime, timezone
from typing import Any

from app.schemas.agronomic_context import VisionDiagnosisInput

from app.services.climate_analysis import ClimateAnalysisService
from app.services.climate_context_builder import ClimateContextBuilder
from app.services.scientific_knowledge import ScientificKnowledgeService
from zoneinfo import ZoneInfo

class AgronomicContextBuilder:

    def __init__(
        self,
        climate_analysis_service: ClimateAnalysisService,
        climate_context_builder: ClimateContextBuilder,
        scientific_knowledge_service: ScientificKnowledgeService,
    ):
        self.climate_analysis_service = climate_analysis_service
        self.climate_context_builder = climate_context_builder
        self.scientific_knowledge_service = scientific_knowledge_service

    def build(
        self,
        diagnosis: VisionDiagnosisInput,
        reference_time: datetime | None = None,
        evidence_limit: int = 20,
    ) -> dict[str, Any]:

        if reference_time is None:
            reference_time = datetime.now(timezone.utc)

        if reference_time.tzinfo is None:
            raise ValueError(
                "reference_time debe incluir zona horaria"
            )

        if not 1 <= evidence_limit <= 100:
            raise ValueError(
                "evidence_limit debe estar entre 1 y 100"
            )

        if not diagnosis.detected_pests and not diagnosis.detected_damages:
            raise ValueError(
                "El diagnóstico debe contener al menos una plaga o un daño."
            )

        # -------------------------------------------------
        # 1. Contexto temporal local
        # -------------------------------------------------

        local_time = reference_time.astimezone(
            ZoneInfo("America/Lima")
        )

        month_names = {
            1: "enero",
            2: "febrero",
            3: "marzo",
            4: "abril",
            5: "mayo",
            6: "junio",
            7: "julio",
            8: "agosto",
            9: "septiembre",
            10: "octubre",
            11: "noviembre",
            12: "diciembre",
        }


        time_context = {
            "reference_time": local_time.isoformat(),
            "year": local_time.year,
            "month": local_time.month,
            "month_name": month_names[local_time.month],
            "timezone": "America/Lima",
        }

        # -------------------------------------------------
        # 2. Construir contexto climático
        # -------------------------------------------------

        climate_analysis = self.climate_analysis_service.analyze(
            station_code=diagnosis.station_code,
            reference_time=reference_time,
        )

        climate_context = self.climate_context_builder.build(
            climate_analysis
        )

        # -------------------------------------------------
        # 3. Recuperar evidencia científica y temporal
        # -------------------------------------------------

        pest_contexts = []
        processed_species = set()

        for pest in diagnosis.detected_pests:

            scientific_name = pest.scientific_name.strip()
            species_key = scientific_name.casefold()

            if species_key in processed_species:
                continue

            processed_species.add(species_key)

            # Evidencia científica:
            # temperatura, humedad, desarrollo y reproducción.
            scientific_result = (
                self.scientific_knowledge_service.search_evidence(
                    scientific_name=scientific_name,
                    limit=evidence_limit,
                )
            )

            # Patrones temporales:
            # presencia poblacional y actividad de crawlers.
            #
            # No filtramos por location porque queremos recuperar
            # también antecedentes de otras localidades productoras.
            temporal_result = (
                self.scientific_knowledge_service.search_temporal_patterns(
                    scientific_name=scientific_name,
                    month=local_time.month,
                    limit=evidence_limit,
                )
            )

            pest_contexts.append({
                "pest": {
                    "scientific_name": scientific_name,
                    "common_name": pest.common_name,
                    "confidence": pest.confidence,
                    "affected_leaf_side": pest.affected_leaf_side,
                },

                "scientific_context": scientific_result,

                "temporal_context": temporal_result,
            })

        # -------------------------------------------------
        # 4. Organizar daños identificados
        # -------------------------------------------------

        damage_contexts = [
            {
                "damage_name": damage.damage_name,
                "description": damage.description,
                "confidence": damage.confidence,
            }
            for damage in diagnosis.detected_damages
        ]

        # -------------------------------------------------
        # 5. Construir contexto agronómico integrado
        # -------------------------------------------------

        return {
            "context_type": "agronomic_context",

            "metadata": {
                "diagnosis_id": diagnosis.diagnosis_id,
                "station_code": diagnosis.station_code,
                "reference_time": local_time.isoformat(),
                "timezone": "America/Lima",
                "crop": {
                    "scientific_name": "Persea americana",
                    "common_name": "Palto",
                    "variety": "Hass",
                },
            },

            "time_context": time_context,

            "diagnosis": {
                "source": "computer_vision",
                "detected_pests": pest_contexts,
                "detected_damages": damage_contexts,
            },

            "climate_context": climate_context,

            "interpretation_guidelines": [
                (
                    "Relacionar la evidencia científica con la "
                    "especie identificada en el diagnóstico."
                ),
                (
                    "No mezclar evidencias de especies diferentes."
                ),
                (
                    "Considerar la confianza del modelo de visión "
                    "al interpretar el diagnóstico."
                ),
                (
                    "Diferenciar una plaga identificada de un daño "
                    "foliar cuya causa no ha sido confirmada."
                ),
                (
                    "Interpretar las condiciones climáticas "
                    "considerando la disponibilidad y calidad "
                    "de las mediciones."
                ),
                (
                    "Comparar los valores climáticos actuales con "
                    "las condiciones experimentales documentadas, "
                    "conservando sus valores y unidades."
                ),
                (
                    "Diferenciar los resultados de laboratorio "
                    "de las observaciones realizadas en campo."
                ),
                (
                    "Utilizar los patrones temporales como "
                    "antecedentes de la localidad donde se "
                    "realizó cada estudio."
                ),
                (
                    "No presentar patrones de otras localidades "
                    "como si fueran observaciones del cultivo actual."
                ),
                (
                    "No afirmar que la población está aumentando "
                    "sin registros poblacionales del cultivo."
                ),
                (
                    "No afirmar causalidad entre las condiciones "
                    "climáticas y la población sin evidencia suficiente."
                ),
            ],
        }