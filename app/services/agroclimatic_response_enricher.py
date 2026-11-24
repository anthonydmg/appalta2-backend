
from app.schemas.agroclimatic_reasoning import (
    AgroclimaticReasoningResponse,
    ClimateObservation,
)
from app.schemas.agroclimatic_report import AgroclimaticReport


class AgroclimaticResponseEnricher:
    """
    Construye el informe agroclimático final.

    Los datos originales del backend tienen prioridad
    sobre los valores generados por el LLM.
    """

    def enrich(
        self,
        response: AgroclimaticReasoningResponse,
        agronomic_context: dict,
    ) -> AgroclimaticReport:

        return AgroclimaticReport(
            climate_conditions=self._enrich_climate_observations(
                response.climate_interpretations,
                agronomic_context,
            ),

            scientific_evidence=response.scientific_evidence,

            seasonal_geographic_context=(
                response.seasonal_geographic_context
            ),

            agroclimatic_assessment=(
                response.agroclimatic_assessment
            ),

            recommendations=response.recommendations,

            limitations=response.limitations,

            overall_conclusion=response.overall_conclusion,
        )

    # -------------------------------------------------
    # ESTADÍSTICAS CLIMÁTICAS
    # -------------------------------------------------

    def _enrich_climate_observations(
        self,
        interpretations: list,
        context: dict,
    ) -> list[ClimateObservation]:

        climate = context.get("climate_context", {})

        # Indexar las interpretaciones de Gemma por periodo y sensor.
        interpretation_index = {
            (
                item.period_days,
                item.sensor_code,
            ): item.interpretation
            for item in interpretations
        }

        enriched = []

        priority_sensors = {
            "ambient_temperature",
            "ambient_humidity",
        }

        for period in climate.get("periods", []):

            period_days = period.get("period_days")

            for sensor in period.get("sensors", []):

                sensor_code = sensor.get("sensor_code")

                if sensor_code not in priority_sensors:
                    continue

                statistics = sensor.get("statistics", {})

                interpretation = interpretation_index.get(
                    (period_days, sensor_code)
                )

                if interpretation is None:
                    interpretation = (
                        "No se generó una interpretación para "
                        "esta variable. Las estadísticas corresponden "
                        "a las mediciones originales de la estación."
                    )

                enriched.append(
                    ClimateObservation(
                        period_days=period_days,
                        variable=sensor.get("sensor_name"),
                        mean=statistics.get("mean"),
                        minimum=statistics.get("minimum"),
                        maximum=statistics.get("maximum"),
                        unit=sensor.get("unit"),
                        interpretation=interpretation,
                    )
                )

        return enriched


    # -------------------------------------------------
    # IDENTIFICACIÓN DE SENSORES
    # -------------------------------------------------

    @staticmethod
    def _resolve_sensor_code(
        variable: str,
        climate: dict,
    ) -> str:

        available_variables = climate.get(
            "available_climate_variables", []
        )

        normalized_variable = variable.strip().lower()

        matches = []

        for sensor in available_variables:

            sensor_name = (
                sensor.get("sensor_name", "").strip().lower()
            )

            sensor_code = sensor.get("sensor_code")

            if normalized_variable in {
                sensor_name,
                sensor_code.lower() if sensor_code else "",
            }:
                matches.append(sensor_code)

        if len(matches) != 1:
            raise ValueError(
                f"No se pudo identificar de forma única "
                f"el sensor correspondiente a '{variable}'."
            )

        return matches[0]
