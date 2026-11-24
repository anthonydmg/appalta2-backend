
import json
from typing import Any

from app.schemas.agroclimatic_reasoning import (
    AgroclimaticReasoningResponse
)


class AgroclimaticPromptBuilder:
    """
    Construye prompts compactos para el razonamiento agroclimático.

    Conserva los hallazgos científicos y las estadísticas climáticas,
    pero elimina metadatos repetidos que no son necesarios
    para la interpretación de Gemma.
    """

    def build(self, agronomic_context: dict[str, Any]) -> str:

        if not isinstance(agronomic_context, dict):
            raise TypeError(
                "El contexto agronómico debe ser un diccionario."
            )

        if not agronomic_context:
            raise ValueError(
                "El contexto agronómico está vacío."
            )

        compact_context = self._compact_context(
            agronomic_context
        )

        context_json = json.dumps(
            compact_context,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str
        )

        output_schema = json.dumps(
            AgroclimaticReasoningResponse.model_json_schema(),
            ensure_ascii=False,
            separators=(",", ":")
        )

        return self._build_instructions(
            context_json=context_json,
            output_schema=output_schema
        )

    # =====================================================
    # COMPACTACIÓN DEL CONTEXTO
    # =====================================================

    def _compact_context(
        self,
        context: dict[str, Any]
    ) -> dict[str, Any]:

        diagnosis = context.get("diagnosis", {})
        climate = context.get("climate_context", {})

        compact_diagnosis = self._compact_diagnosis(
            diagnosis
        )

        compact_climate = self._compact_climate(
            climate
        )

        return {
            "metadata": context.get("metadata", {}),
            "diagnosis": compact_diagnosis,
            "climate": compact_climate,
            "interpretation_guidelines": (
                context.get("interpretation_guidelines", [])
            )
        }

    # =====================================================
    # DIAGNÓSTICO Y EVIDENCIA CIENTÍFICA
    # =====================================================

    def _compact_diagnosis(
        self,
        diagnosis: dict[str, Any]
    ) -> dict[str, Any]:

        detected_pests = diagnosis.get(
            "detected_pests", []
        )

        compact_pests = []

        for detected in detected_pests:

            pest = detected.get("pest", {})
            scientific_context = detected.get(
                "scientific_context", {}
            )

            evidence_list = scientific_context.get(
                "evidence", []
            )

            compact_evidence = []
            studies = {}

            for evidence in evidence_list:

                document_code = evidence.get(
                    "document_code"
                )

                # Agrupar metadatos bibliográficos por estudio.
                if document_code and document_code not in studies:

                    studies[document_code] = {
                        "document_code": document_code,
                        "title": evidence.get("source_title"),
                        "authors": evidence.get("authors", []),
                        "year": evidence.get("publication_year"),
                        "study_type": evidence.get("study_type"),
                        "study_location": evidence.get("study_location")
                    }

                # Mantener los datos científicos de cada evidencia.
                compact_evidence.append({
                    "evidence_code": evidence.get(
                        "evidence_code"
                    ),
                    "document_code": document_code,
                    "climate_variable": evidence.get(
                        "climate_variable"
                    ),
                    "biological_response": evidence.get(
                        "biological_response"
                    ),
                    "finding": evidence.get("finding"),
                    "conditions": evidence.get("conditions", {}),
                    "result": evidence.get("result", {}),
                    "evidence_type": evidence.get(
                        "evidence_type"
                    ),
                    "statistical_support": evidence.get(
                        "statistical_support"
                    ),
                    "interpretation_limit": evidence.get(
                        "interpretation_limit"
                    ),
                    "validation_status": evidence.get(
                        "validation_status"
                    )
                })

            compact_pests.append({
                "pest": {
                    "scientific_name": pest.get(
                        "scientific_name"
                    ),
                    "common_name": pest.get("common_name"),
                    "confidence": pest.get("confidence"),
                    "affected_leaf_side": pest.get(
                        "affected_leaf_side"
                    )
                },
                "retrieval": {
                    "total_evidences": scientific_context.get(
                        "retrieval", {}
                    ).get("total_evidences", len(evidence_list)),
                    "returned_evidences": len(evidence_list)
                },
                "studies": list(studies.values()),
                "evidence": compact_evidence
            })

        detected_damages = diagnosis.get(
            "detected_damages", []
        )

        compact_damages = [
            {
                "damage_name": damage.get("damage_name"),
                "description": damage.get("description"),
                "confidence": damage.get("confidence")
            }
            for damage in detected_damages
        ]

        return {
            "source": diagnosis.get("source"),
            "detected_pests": compact_pests,
            "detected_damages": compact_damages
        }

    # =====================================================
    # CONTEXTO CLIMÁTICO
    # =====================================================

    def _compact_climate(
        self,
        climate: dict[str, Any]
    ) -> dict[str, Any]:

        compact_periods = []

        for period in climate.get("periods", []):

            compact_sensors = []

            for sensor in period.get("sensors", []):

                statistics = sensor.get(
                    "statistics", {}
                )

                availability = sensor.get(
                    "data_availability", {}
                )

                quality = sensor.get(
                    "data_quality", {}
                )

                compact_sensors.append({
                    "sensor_code": sensor.get("sensor_code"),
                    "sensor_name": sensor.get("sensor_name"),
                    "unit": sensor.get("unit"),

                    "statistics": {
                        "mean": statistics.get("mean"),
                        "minimum": statistics.get("minimum"),
                        "maximum": statistics.get("maximum")
                    },

                    "data_availability": {
                        "sample_count": availability.get(
                            "sample_count"
                        ),
                        "expected_count": availability.get(
                            "expected_count"
                        ),
                        "coverage_percentage": availability.get(
                            "sample_coverage_percentage"
                        ),
                        "first_measurement": availability.get(
                            "first_measurement"
                        ),
                        "last_measurement": availability.get(
                            "last_measurement"
                        ),
                        "max_gap_hours": availability.get(
                            "max_gap_hours"
                        )
                    },

                    "data_quality": {
                        "zero_count": quality.get("zero_count", 0),
                        "observations": quality.get(
                            "observations", []
                        )
                    }
                })

            compact_periods.append({
                "period_days": period.get("period_days"),
                "start_time": period.get("start_time"),
                "end_time": period.get("end_time"),
                "sensors": compact_sensors
            })

        return {
            "station_code": climate.get("station_code"),
            "reference_time": climate.get("reference_time"),
            "sampling_interval_minutes": climate.get(
                "sampling_interval_minutes"
            ),
            "periods": compact_periods,
            "available_climate_variables": climate.get(
                "available_climate_variables", []
            ),
            "unavailable_climate_variables": climate.get(
                "unavailable_climate_variables", []
            ),
            "interpretation_guidelines": climate.get(
                "interpretation_guidelines", []
            )
        }

    # =====================================================
    # INSTRUCCIONES DEL MODELO
    # =====================================================

    @staticmethod
    def _build_instructions(
        context_json: str,
        output_schema: str
    ) -> str:

        return f"""
Eres un asistente especializado en razonamiento
agroclimático y conocimiento científico del cultivo
de palto Hass (Persea americana).

OBJETIVO

Analizar conjuntamente:

1. El diagnóstico de la plaga realizado por visión artificial.
2. Las condiciones climáticas medidas por la estación.
3. La evidencia científica disponible para la especie.

No eres un sistema de diagnóstico visual.
No debes volver a identificar ni modificar la plaga.

==================================================
CONTEXTO AGRONÓMICO
==================================================

{context_json}

==================================================
PROCEDIMIENTO DE RAZONAMIENTO
==================================================

1. DIAGNÓSTICO

- Identifica la especie y considera la confianza del modelo.
- Considera la superficie foliar afectada.
- Diferencia una plaga identificada de un daño cuya causa
  no haya sido confirmada.

2. CONDICIONES CLIMÁTICAS

Analiza los períodos de 7, 15 y 30 días.

Considera:
- Media, mínimo y máximo.
- Número de muestras y cobertura.
- Primera y última medición.
- Brecha máxima entre mediciones.
- Observaciones de calidad.

No confundas cobertura con continuidad temporal.
Una cobertura del 100 % no garantiza continuidad.
No interpretes los promedios como observaciones continuas
cuando existan brechas prolongadas.

No inventes precipitaciones ni otras variables ausentes.
No descartes automáticamente valores iguales a cero.
No modifiques los valores estadísticos proporcionados.

3. EVIDENCIA CIENTÍFICA

Examina los hallazgos individuales y sus códigos.

Distingue:
- Estudios de laboratorio y de campo.
- Condiciones experimentales y observaciones de campo.
- Asociaciones estadísticas y relaciones causales.
- Resultados medidos e interpretaciones de autores.

No extrapoles directamente resultados de laboratorio
a condiciones de campo.

No conviertas temperaturas experimentales en umbrales
universales de riesgo.

Considera siempre el campo interpretation_limit
de cada evidencia.

Las evidencias con estado
EXTRACTED_PENDING_AGRONOMIC_VALIDATION
son hallazgos extraídos pendientes de validación
agronómica. No son conocimiento agronómico validado.

4. RELACIÓN CLIMA-PLAGA

Compara las condiciones observadas con los estudios.

Distingue:
- Coincidencia de condiciones ambientales.
- Asociación estadística.
- Respuesta biológica experimental.
- Causalidad demostrada.

No afirmes que el clima favoreció, incrementó o redujo
la población de la plaga sin respaldo suficiente.

Respeta los estudios que reporten ausencia de correlación.

Si los estudios presentan resultados diferentes,
explica sus diferencias metodológicas y contextuales.

5. EVALUACIÓN AGROCLIMÁTICA

Elabora una evaluación considerando:
- Diagnóstico.
- Condiciones climáticas.
- Calidad y continuidad de datos.
- Evidencia científica.
- Limitaciones de extrapolación.

La presencia de una plaga no demuestra que el clima
haya causado su presencia.

6. RECOMENDACIONES

Prioriza acciones justificables de:
- Monitoreo de la plaga.
- Seguimiento de su distribución en el árbol.
- Inspección de la superficie foliar afectada.
- Seguimiento de variables climáticas relevantes.
- Obtención de datos adicionales.

Distingue respaldo científico directo, indirecto
y precauciones de criterio experto.

No prescribas productos químicos, dosis ni frecuencias
de aplicación sin información suficiente.

7. LIMITACIONES

Identifica:
- Variables no disponibles.
- Cobertura insuficiente.
- Brechas prolongadas.
- Mediciones sospechosas.
- Evidencias pendientes de validación.
- Relaciones científicas no demostradas.

==================================================
REGLAS OBLIGATORIAS
==================================================

1. Utiliza exclusivamente los datos del contexto.
2. No inventes cifras, estudios ni referencias.
3. No modifiques estadísticas originales.
4. No confundas ausencia de información con ausencia
   de un fenómeno biológico.
5. No afirmes causalidad sin evidencia suficiente.
6. Cada hallazgo científico debe citar su evidence_code.
7. No atribuyas resultados a estudios que no los respaldan.
8. No inventes recomendaciones específicas.
9. Si falta información, indícalo expresamente.
10. Conserva la incertidumbre científica.

==================================================
FORMATO DE SALIDA
==================================================

Devuelve exclusivamente un objeto JSON válido
que cumpla el siguiente esquema:

{output_schema}

No incluyas Markdown ni bloques de código.
La respuesta debe estar redactada en español.
Utiliza null o listas vacías cuando corresponda.
Respeta los valores permitidos por los campos Literal.
"""
