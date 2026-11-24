
import json
from typing import Any

from app.schemas.agroclimatic_reasoning import (
    AgroclimaticReasoningResponse,
)


PRIORITY_CLIMATE_VARIABLES = {
    "ambient_temperature",
    "ambient_humidity",
}


class AgroclimaticPromptBuilderV2:
    """
    Construye un prompt agroclimático compacto.

    Conserva los datos científicos originales y reduce
    la redundancia de metadatos e instrucciones.

    Gemma genera interpretaciones y contenido narrativo.
    Los datos determinísticos serán incorporados posteriormente
    por el backend mediante AgroclimaticResponseEnricher.
    """

    def __init__(
        self,
        expected_evidence_count: int | None = None,
    ):
        self.expected_evidence_count = expected_evidence_count

    # =====================================================
    # CONSTRUCCIÓN DEL PROMPT
    # =====================================================

    def build(
        self,
        agronomic_context: dict[str, Any],
    ) -> str:

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

        pests = compact_context["diagnosis"]["pests"]

        evidence_count = sum(
            pest["retrieval"]["returned_evidences"]
            for pest in pests
        )

        if (
            self.expected_evidence_count is not None
            and evidence_count != self.expected_evidence_count
        ):
            raise ValueError(
                f"Se esperaban {self.expected_evidence_count} evidencias, "
                f"pero se encontraron {evidence_count}."
            )

        context_json = json.dumps(
            compact_context,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )

        output_schema = self._compact_schema(
            AgroclimaticReasoningResponse.model_json_schema()
        )

        return self._build_instructions(
            context_json=context_json,
            output_schema=json.dumps(
                output_schema,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        )

    # =====================================================
    # CONTEXTO GENERAL
    # =====================================================

    def _compact_context(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        diagnosis = context.get("diagnosis")

        if not isinstance(diagnosis, dict):
            raise ValueError(
                "No se encontró un objeto diagnosis válido."
            )

        metadata = context.get("metadata", {})
        climate_context = context.get("climate_context", {})

        return {
            "metadata": {
                "diagnosis_id": metadata.get("diagnosis_id"),
                "station_code": metadata.get("station_code"),
                "reference_time": metadata.get("reference_time"),
                "timezone": metadata.get("timezone"),
            },

            "crop": metadata.get("crop", {}),

            "time": context.get("time_context", {}),

            "location": climate_context.get("location"),

            "diagnosis": self._compact_diagnosis(
                diagnosis
            ),

            "climate": self._compact_climate(
                climate_context
            ),

            "guidelines": context.get(
                "interpretation_guidelines",
                [],
            ),
        }

    # =====================================================
    # DIAGNÓSTICO Y EVIDENCIAS
    # =====================================================

    def _compact_diagnosis(
        self,
        diagnosis: dict[str, Any],
    ) -> dict[str, Any]:

        compact_pests = []

        for detected in diagnosis.get("detected_pests", []):

            pest = detected.get("pest", {})

            scientific_context = detected.get(
                "scientific_context",
                {},
            )

            evidence_list = scientific_context.get(
                "evidence",
                detected.get("evidence", []),
            )

            retrieval = scientific_context.get(
                "retrieval",
                detected.get("retrieval", {}),
            )

            if not evidence_list:
                raise ValueError(
                    "No se encontraron evidencias científicas para "
                    f"{pest.get('scientific_name', 'especie desconocida')}. "
                    f"Claves disponibles: {list(detected.keys())}"
                )

            # -------------------------------------------------
            # 1. ESTUDIOS Y EVIDENCIAS CIENTÍFICAS
            # -------------------------------------------------

            studies = {}
            compact_evidence = []

            for evidence in evidence_list:

                document_code = evidence.get("document_code")

                if document_code and document_code not in studies:
                    studies[document_code] = {
                        "code": document_code,

                        "authors": self._compact_authors(
                            evidence.get("authors", [])
                        ),

                        "year": evidence.get("publication_year"),

                        "type": evidence.get("study_type"),

                        "location": evidence.get("study_location"),
                    }

                compact_evidence.append({
                    "code": evidence.get("evidence_code"),

                    "study": document_code,

                    "variable": evidence.get("climate_variable"),

                    "response": evidence.get("biological_response"),

                    "finding": evidence.get("finding"),

                    "conditions": evidence.get("conditions", {}),

                    "result": evidence.get("result", {}),

                    "type": evidence.get("evidence_type"),

                    "statistics": evidence.get(
                        "statistical_support"
                    ),

                    "limit": evidence.get(
                        "interpretation_limit"
                    ),

                    "validation": evidence.get(
                        "validation_status"
                    ),
                })

            # -------------------------------------------------
            # 2. PATRONES TEMPORALES
            # -------------------------------------------------

            temporal_context = detected.get(
                "temporal_context",
                {},
            )

            temporal_patterns = temporal_context.get(
                "patterns",
                [],
            )

            temporal_retrieval = temporal_context.get(
                "retrieval",
                {},
            )

            compact_temporal_patterns = []

            for pattern in temporal_patterns:

                compact_temporal_patterns.append({

                    "pattern_type": pattern.get(
                        "pattern_type"
                    ),

                    "period": pattern.get(
                        "period_label"
                    ),

                    "months": pattern.get(
                        "months",
                        [],
                    ),

                    "seasonal_context": pattern.get(
                        "seasonal_context"
                    ),

                    "evidence": {
                        "code": pattern.get(
                            "evidence_code"
                        ),

                        "finding": pattern.get(
                            "finding"
                        ),

                        "result": pattern.get(
                            "result_data",
                            {},
                        ),

                        "type": pattern.get(
                            "evidence_type"
                        ),

                        "statistics": pattern.get(
                            "statistical_support"
                        ),

                        "limit": pattern.get(
                            "interpretation_limit"
                        ),

                        "validation": pattern.get(
                            "validation_status"
                        ),
                    },

                    "study": {
                        "id": pattern.get(
                            "study_id"
                        ),

                        "type": pattern.get(
                            "study_type"
                        ),

                        "location": pattern.get(
                            "study_location"
                        ),

                        "locations": pattern.get(
                            "study_locations",
                            [],
                        ),
                    },
                })

            # -------------------------------------------------
            # 3. CONTEXTO COMPACTO DE LA PLAGA
            # -------------------------------------------------

            compact_pests.append({

                "pest": {
                    "scientific_name": pest.get(
                        "scientific_name"
                    ),

                    "common_name": pest.get(
                        "common_name"
                    ),

                    "confidence": pest.get(
                        "confidence"
                    ),

                    "leaf_side": pest.get(
                        "affected_leaf_side"
                    ),
                },

                "retrieval": {
                    "total_evidences": retrieval.get(
                        "total_evidences",
                        len(evidence_list),
                    ),

                    "returned_evidences": len(
                        evidence_list
                    ),
                },

                "studies": list(
                    studies.values()
                ),

                "evidence": compact_evidence,

                "temporal_patterns": {
                    "total_patterns": temporal_retrieval.get(
                        "total_patterns",
                        len(temporal_patterns),
                    ),

                    "has_results": temporal_retrieval.get(
                        "has_results",
                        bool(temporal_patterns),
                    ),

                    "patterns": compact_temporal_patterns,
                },
            })

        # -----------------------------------------------------
        # 4. DAÑOS DETECTADOS
        # -----------------------------------------------------

        compact_damages = [
            {
                "name": damage.get("damage_name"),

                "description": damage.get("description"),

                "confidence": damage.get("confidence"),
            }

            for damage in diagnosis.get(
                "detected_damages",
                [],
            )
        ]

        return {
            "source": diagnosis.get("source"),

            "pests": compact_pests,

            "damages": compact_damages,
        }

    # =====================================================
    # AUTORES
    # =====================================================

    @staticmethod
    def _compact_authors(
        authors: Any,
    ) -> Any:
        """
        Evita repetir nombres extensos de autores.
        No inventa ni sustituye apellidos.
        """

        if not authors:
            return []

        if isinstance(authors, str):
            return authors.strip()

        if isinstance(authors, list):
            return [
                author.strip()
                for author in authors
                if isinstance(author, str) and author.strip()
            ]

        return authors

    # =====================================================
    # CONTEXTO CLIMÁTICO
    # =====================================================

    def _compact_climate(
        self,
        climate: dict[str, Any],
    ) -> dict[str, Any]:

        periods = []

        for period in climate.get("periods", []):

            sensors = []

            for sensor in period.get("sensors", []):

                sensor_code = sensor.get("sensor_code")

                if sensor_code not in PRIORITY_CLIMATE_VARIABLES:
                    continue

                stats = sensor.get("statistics", {})

                availability = sensor.get(
                    "data_availability",
                    {},
                )

                quality = sensor.get(
                    "data_quality",
                    {},
                )

                sensors.append({

                    "code": sensor.get(
                        "sensor_code"
                    ),

                    "name": sensor.get(
                        "sensor_name"
                    ),

                    "unit": sensor.get(
                        "unit"
                    ),

                    "stats": {
                        "mean": stats.get("mean"),

                        "min": stats.get("minimum"),

                        "max": stats.get("maximum"),
                    },

                    "availability": {
                        "n": availability.get(
                            "sample_count"
                        ),

                        "expected": availability.get(
                            "expected_count"
                        ),

                        "coverage_pct": availability.get(
                            "sample_coverage_percentage"
                        ),

                        "first": availability.get(
                            "first_measurement"
                        ),

                        "last": availability.get(
                            "last_measurement"
                        ),

                        "max_gap_hours": availability.get(
                            "max_gap_hours"
                        ),
                    },

                    "quality": {
                        "zero_count": quality.get(
                            "zero_count",
                            0,
                        ),

                        "observations": quality.get(
                            "observations",
                            [],
                        ),
                    },
                })

            periods.append({

                "days": period.get(
                    "period_days"
                ),

                "start": period.get(
                    "start_time"
                ),

                "end": period.get(
                    "end_time"
                ),

                "sensors": sensors,
            })

        return {
            "station": climate.get(
                "station_code"
            ),

            "reference_time": climate.get(
                "reference_time"
            ),

            "sampling_interval_min": climate.get(
                "sampling_interval_minutes"
            ),

            "periods": periods,

            "available_variables": climate.get(
                "available_climate_variables",
                [],
            ),

            "unavailable_variables": climate.get(
                "unavailable_climate_variables",
                [],
            ),

            "guidelines": climate.get(
                "interpretation_guidelines",
                [],
            ),
        }

    # =====================================================
    # ESQUEMA JSON COMPACTO
    # =====================================================

    @classmethod
    def _compact_schema(
        cls,
        schema: Any,
    ) -> Any:
        """
        Elimina metadatos descriptivos del JSON Schema,
        conservando tipos, propiedades, referencias, enums
        y campos obligatorios.
        """

        if isinstance(schema, list):
            return [
                cls._compact_schema(item)
                for item in schema
            ]

        if isinstance(schema, dict):

            excluded = {
                "title",
                "description",
                "default",
                "examples",
            }

            return {
                key: cls._compact_schema(value)
                for key, value in schema.items()
                if key not in excluded
            }

        return schema

    # =====================================================
    # CONSTRUCCIÓN DE SECCIONES DEL PROMPT
    # =====================================================

    def build_sections(
        self,
        agronomic_context: dict[str, Any],
    ) -> dict[str, str]:
        """
        Construye las secciones del prompt por separado
        para analizar su tamaño.
        """

        compact_context = self._compact_context(
            agronomic_context
        )

        context_json = json.dumps(
            compact_context,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )

        output_schema = json.dumps(
            self._compact_schema(
                AgroclimaticReasoningResponse.model_json_schema()
            ),
            ensure_ascii=False,
            separators=(",", ":"),
        )

        instructions = self._build_instructions(
            context_json="",
            output_schema="",
        )

        return {

            "instructions": instructions,

            "metadata": json.dumps(
                compact_context["metadata"],
                ensure_ascii=False,
                separators=(",", ":"),
            ),

            "crop": json.dumps(
                compact_context["crop"],
                ensure_ascii=False,
                separators=(",", ":"),
            ),

            "time": json.dumps(
                compact_context["time"],
                ensure_ascii=False,
                separators=(",", ":"),
            ),

            "location": json.dumps(
                compact_context["location"],
                ensure_ascii=False,
                separators=(",", ":"),
            ),

            "diagnosis": json.dumps(
                compact_context["diagnosis"],
                ensure_ascii=False,
                separators=(",", ":"),
            ),

            "climate": json.dumps(
                compact_context["climate"],
                ensure_ascii=False,
                separators=(",", ":"),
            ),

            "guidelines": json.dumps(
                compact_context["guidelines"],
                ensure_ascii=False,
                separators=(",", ":"),
            ),

            "schema": output_schema,

            "context": context_json,

            "full_prompt": self.build(
                agronomic_context
            ),
        }

    # =====================================================
    # INSTRUCCIONES PARA GEMMA
    # =====================================================

    @staticmethod
    def _build_instructions(
        context_json: str,
        output_schema: str,
    ) -> str:

        return f"""
Eres un asistente especializado en razonamiento agroclimático
del cultivo de palto Hass (Persea americana).

Tu responsabilidad es interpretar conjuntamente el diagnóstico
de visión artificial, las observaciones climáticas, la evidencia
científica y los patrones temporales disponibles.

No vuelvas a diagnosticar la plaga ni modifiques su identidad.

Debes producir una evaluación agronómica fundamentada,
prudente y trazable a los datos proporcionados.

============================================================
1. CONTEXTO DE ANÁLISIS
============================================================

CONTEXTO:

{context_json}

Toda afirmación debe estar respaldada por la información
contenida en este contexto.

============================================================
2. PROCEDIMIENTO DE RAZONAMIENTO
============================================================

Antes de construir la respuesta JSON, realiza internamente
las siguientes etapas en orden.

------------------------------------------------------------
ETAPA 1. IDENTIFICACIÓN DEL CASO
------------------------------------------------------------

Identifica:

- Cultivo.
- Plagas detectadas.
- Confianza de cada diagnóstico.
- Parte de la hoja afectada.
- Daños detectados.
- Fecha de referencia.
- Ubicación de la estación meteorológica.

Respeta las identidades proporcionadas por visión artificial.

No interpretes la confianza como densidad poblacional,
severidad ni confirmación de campo.

Diferencia una plaga identificada de un daño foliar
cuya causa no ha sido confirmada.

No mezcles evidencias de especies diferentes.

------------------------------------------------------------
ETAPA 2. ANÁLISIS DE OBSERVACIONES CLIMÁTICAS
------------------------------------------------------------

Examina individualmente las ventanas temporales disponibles,
especialmente los períodos de 7, 15 y 30 días.

Para cada variable considera:

- Media.
- Valor mínimo.
- Valor máximo.
- Número de muestras.
- Cobertura.
- Primera y última medición.
- Brecha máxima.
- Observaciones de calidad.

Reglas:

- Respeta las estadísticas proporcionadas.
- Los ceros se contabilizan como observaciones de calidad,
  pero no participan en la media, mínimo ni máximo.
- No recalcules las estadísticas.
- No inventes precipitaciones ni variables ausentes.
- La cobertura de muestras no garantiza continuidad temporal.
- Si dos períodos tienen los mismos valores, no asumas
  que representan observaciones independientes.
- Si no hay mediciones recientes, no presentes estadísticas
  antiguas como condiciones actuales.
- La humedad del suelo es una variable edáfica y no
  debe confundirse con la humedad atmosférica.

Para generar climate_interpretations:

- Genera una interpretación por cada combinación de período
  y sensor prioritario disponible.
- Utiliza period_days para identificar la ventana temporal.
- Utiliza exactamente el código original del sensor
  en sensor_code.
- No devuelvas medias, mínimos, máximos ni unidades.
  Estos valores serán incorporados posteriormente por el backend.
- No inventes interpretaciones cuando no existan
  mediciones suficientes.
- No confundas las ventanas de 7, 15 y 30 días.
- No generes interpretaciones para sensores que no aparecen
  en el contexto climático.

------------------------------------------------------------
ETAPA 3. ANÁLISIS INDIVIDUAL DE EVIDENCIAS
------------------------------------------------------------

Examina las evidencias científicas disponibles para cada especie.

Para cada evidencia identifica:

1. Código de evidencia.
2. Estudio al que pertenece.
3. Tipo de estudio: laboratorio o campo.
4. Variable o respuesta biológica estudiada.
5. Condiciones experimentales o ambientales.
6. Resultado observado.
7. Limitaciones de interpretación.
8. Estado de validación.

Clasifica su aporte al caso:

- Relevante para las condiciones climáticas.
- Relevante para el desarrollo biológico de la plaga.
- Relevante para los patrones estacionales.
- Relevante para el manejo o monitoreo.
- Evidencia sin relación directa con el caso actual.

No todas las evidencias tienen que incluirse en
scientific_findings.

Selecciona las que aporten información concreta
para interpretar el caso.

Conserva los resultados positivos y negativos.

No atribuyas a una evidencia los resultados de otra.

EXTRACTED_PENDING_AGRONOMIC_VALIDATION significa que
la información está pendiente de validación agronómica.
No debe presentarse como conocimiento validado.

Para generar scientific_findings:

Cada elemento debe incluir:

- scientific_name: nombre científico exacto de la especie.
- evidence_code: código original de la evidencia.
- relevance_to_current_conditions: explicación de su relevancia.

No inventes códigos de evidencia.

No utilices códigos pertenecientes a otra especie.

No modifiques el estado de validación original.

Para generar scientific_evidence:

Construye un texto técnico y comprensible que sintetice
los hallazgos científicos relevantes.

Debe:

- Diferenciar los resultados de laboratorio y campo.
- Explicar los resultados relevantes para el caso.
- Conservar los resultados positivos y negativos.
- Explicar los límites de interpretación de los estudios.
- Diferenciar evidencia validada de evidencia pendiente
  de validación agronómica.

No menciones autores por nombre al agricultor.

No presentes evidencia pendiente de validación
como conocimiento científicamente validado.

No inventes resultados ni atribuciones.

------------------------------------------------------------
ETAPA 4. ANÁLISIS DE PATRONES TEMPORALES Y GEOGRÁFICOS
------------------------------------------------------------

Examina los patrones temporales recuperados para cada plaga.

Para cada patrón identifica:

- Meses documentados.
- Tipo de comportamiento observado.
- Localidad del estudio.
- Tipo de evidencia.
- Resultado y limitaciones.

Compara el mes de referencia con los meses documentados.

Distingue:

A. Coincidencia temporal:

El mes actual coincide con un período documentado.

B. Coincidencia geográfica:

La ubicación actual corresponde a la localidad del estudio.

C. Diferencia geográfica:

El patrón procede de otra localidad y su extrapolación
requiere precaución.

Una coincidencia temporal no demuestra que el comportamiento
biológico sea idéntico en otra localidad.

No confundas actividad de migrantes con incremento
de densidad poblacional.

No interpretes patrones estacionales como efectos causados
por temperatura o humedad si el estudio no lo demuestra.

Para generar seasonal_geographic_context:

Construye un texto que explique los antecedentes
estacionales y geográficos pertinentes.

Incluye cuando corresponda:

- Meses de mayor o menor presencia documentada.
- Períodos de actividad de estados migrantes.
- Localidades donde se realizaron los estudios.
- Coincidencia entre el mes actual y los períodos documentados.
- Diferencias geográficas entre los estudios y la ubicación actual.

No presentes patrones de otras localidades
como observaciones del cultivo actual.

Si no existen patrones temporales pertinentes,
indícalo explícitamente.

------------------------------------------------------------
ETAPA 5. INTEGRACIÓN AGROCLIMÁTICA
------------------------------------------------------------

Integra los resultados de las etapas anteriores.

Evalúa separadamente:

- Qué demuestra el diagnóstico.
- Qué muestran las observaciones climáticas.
- Qué resultados científicos son pertinentes.
- Qué coincidencias ambientales existen.
- Qué patrones temporales coinciden.
- Qué limitaciones afectan la interpretación.

Distingue cuatro niveles de evidencia:

1. Coincidencia ambiental:

Los valores observados coinciden con condiciones
registradas en un estudio.

2. Asociación estadística:

Un estudio documenta una asociación entre variables.

3. Respuesta experimental:

Un estudio observa una respuesta bajo condiciones
experimentales controladas.

4. Causalidad demostrada:

Existe evidencia suficiente para establecer una relación
causal en las condiciones estudiadas.

No confundas estos niveles.

No afirmes que la plaga aumenta, disminuye o se reproduce
más rápidamente si los datos no lo demuestran.

Para agroclimatic_assessment genera:

- assessment: evaluación agroclimática integrada.
- evidence_strength: fuerza de la evidencia disponible.
- causal_relationship_established: indica si existe
  evidencia suficiente para establecer causalidad.
- justification: justificación de la evaluación.

Utiliza exclusivamente los valores permitidos por el esquema
para evidence_strength:

- strong
- moderate
- limited
- insufficient

No confundas fuerza de evidencia con nivel de riesgo.

No asignes niveles de riesgo no sustentados.

La categoría de vigilancia fitosanitaria será determinada
posteriormente por el backend, no por esta respuesta.

------------------------------------------------------------
ETAPA 6. FORMULACIÓN DE RECOMENDACIONES
------------------------------------------------------------

Deriva las recomendaciones de los hallazgos y limitaciones
identificados.

Considera las siguientes acciones cuando sean pertinentes:

- Inspeccionar el envés de las hojas.
- Verificar individuos vivos y hembras grávidas.
- Identificar y monitorear estados migrantes.
- Registrar presencia y abundancia de la plaga.
- Observar enemigos naturales y parasitoides.
- Comparar registros de monitoreo anteriores.
- Mejorar la disponibilidad de información climática.

Clasifica cada recomendación:

monitoring:
Acciones de inspección, observación y seguimiento.

preventive:
Medidas preventivas prudentes que no implican
que exista un incremento poblacional confirmado.

management:
Acciones de manejo respaldadas por información suficiente.

Indica el tipo de respaldo:

direct:
La evidencia respalda directamente la acción.

indirect:
La recomendación se deriva indirectamente de los hallazgos.

expert_precaution:
Medida prudencial ante incertidumbre o falta de información.

not_established:
No existe respaldo científico suficiente para establecerla.

No prescribas productos, dosis ni tratamientos específicos
sin evidencia suficiente.

No generes recomendaciones genéricas que no tengan
relación con el diagnóstico o el contexto analizado.

------------------------------------------------------------
ETAPA 7. IDENTIFICACIÓN DE LIMITACIONES
------------------------------------------------------------

Identifica las limitaciones que realmente afectan
la interpretación del caso.

Considera:

- Ausencia de variables climáticas relevantes.
- Falta de mediciones recientes.
- Cobertura insuficiente.
- Brechas temporales.
- Mediciones con problemas de calidad.
- Evidencia pendiente de validación agronómica.
- Diferencias entre localidades de estudio y estación actual.
- Resultados exclusivamente experimentales.
- Ausencia de monitoreo poblacional en campo.
- Falta de evidencia causal.

Para cada limitación explica:

1. Qué información falta o qué restricción existe.
2. Cómo afecta la interpretación agroclimática.

No confundas ausencia de información con ausencia
del fenómeno biológico.

------------------------------------------------------------
ETAPA 8. CONSTRUCCIÓN DE LA CONCLUSIÓN
------------------------------------------------------------

Construye overall_conclusion utilizando exclusivamente
los resultados de las etapas anteriores.

Resume:

- Plagas identificadas.
- Condiciones climáticas observadas.
- Evidencias científicas relevantes.
- Coincidencias temporales y geográficas.
- Resultado de la evaluación agroclimática.
- Incertidumbres principales.
- Acción prioritaria recomendada.

No introduzcas nuevos hallazgos en esta sección.

============================================================
3. REGLAS CIENTÍFICAS Y AGRONÓMICAS
============================================================

IDENTIDAD:

- Persea americana corresponde al cultivo.
- La identidad de cada plaga debe obtenerse del diagnóstico.
- No intercambies la identidad del cultivo y las plagas.
- No mezcles evidencias de especies diferentes.
- No modifiques el diagnóstico original.

EVIDENCIA:

- Cada hallazgo científico debe identificar su evidence_code.
- Cada interpretación debe corresponder a su scientific_name.
- No inventes autores, resultados ni estadísticas.
- Distingue laboratorio y campo.
- Respeta los resultados negativos.
- No conviertas resultados experimentales en umbrales
  universales de riesgo.
- Conserva los estados de validación originales.

CLIMA Y CAUSALIDAD:

- No infieras causalidad por coincidencia de valores.
- No atribuyas incrementos poblacionales al clima
  sin evidencia que lo demuestre.
- Respeta las evidencias que indiquen ausencia
  de correlación.
- No confundas estacionalidad con causalidad climática.

INCERTIDUMBRE:

- Diferencia observaciones actuales de antecedentes.
- No extrapoles automáticamente resultados entre localidades.
- No afirmes evolución poblacional sin registros de campo.
- No asignes niveles de riesgo no sustentados.

============================================================
4. CONSTRUCCIÓN DE LA RESPUESTA
============================================================

La respuesta generada será utilizada por el backend
para construir un informe agroclimático de seis secciones.

Cada campo tiene una responsabilidad específica:

climate_interpretations:

Interpretaciones climáticas asociadas a cada período
y código de sensor.

scientific_findings:

Relaciones entre evidencias científicas originales
y las condiciones actuales.

scientific_evidence:

Texto de la sección que sintetiza los hallazgos científicos.

seasonal_geographic_context:

Texto de la sección que explica los antecedentes
temporales y geográficos.

agroclimatic_assessment:

Evaluación integrada y justificación.

recommendations:

Lista de recomendaciones agronómicas.

limitations:

Lista de limitaciones que afectan la interpretación.

overall_conclusion:

Conclusión general del análisis.

El diagnóstico original y las estadísticas climáticas
serán incorporados por el backend.

Evita repetir literalmente la misma información
en varias secciones.

No utilices listas vacías cuando existan datos pertinentes
para desarrollar el campo correspondiente.

Utiliza listas vacías únicamente cuando no exista
información pertinente.

No inventes información para completar campos.

============================================================
5. FORMATO DE SALIDA
============================================================

Devuelve exclusivamente JSON válido en español.

Respeta exactamente el siguiente esquema:

{output_schema}

No agregues propiedades.

No incluyas Markdown.

No incluyas explicaciones fuera del JSON.
"""
