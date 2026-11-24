
from app.schemas.climate_analysis import ClimateAnalysisResponse


class ClimateContextBuilder:

    def build(
        self,
        analysis: ClimateAnalysisResponse,
    ) -> dict:

        # -------------------------------------------------
        # UBICACIÓN DE LA ESTACIÓN
        # -------------------------------------------------

        location = (
            analysis.location.model_dump()
            if analysis.location is not None
            else None
        )

        # -------------------------------------------------
        # PERÍODOS CLIMÁTICOS
        # -------------------------------------------------

        periods = []

        for period in analysis.periods:

            sensors = []

            for sensor in period.sensors:

                observations = self._build_sensor_observations(
                    sensor
                )

                sensors.append({
                    "sensor_code": sensor.sensor_code,
                    "sensor_name": sensor.sensor_name,
                    "unit": sensor.unit,

                    "statistics": {
                        "mean": sensor.mean,
                        "minimum": sensor.minimum,
                        "maximum": sensor.maximum,
                    },

                    "data_availability": {
                        "sample_count": sensor.sample_count,
                        "valid_sample_count": sensor.valid_sample_count,
                        "expected_count": sensor.expected_count,
                        "sample_coverage_percentage": (
                            sensor.coverage_percentage
                        ),
                        "first_measurement": (
                            sensor.first_measurement.isoformat()
                            if sensor.first_measurement
                            else None
                        ),
                        "last_measurement": (
                            sensor.last_measurement.isoformat()
                            if sensor.last_measurement
                            else None
                        ),
                        "max_gap_minutes": sensor.max_gap_minutes,
                        "max_gap_hours": (
                            round(sensor.max_gap_minutes / 60, 2)
                            if sensor.max_gap_minutes is not None
                            else None
                        ),
                    },

                    "data_quality": {
                        "zero_count": sensor.zero_count,
                        "observations": observations,
                    },
                })

            periods.append({
                "period_days": period.period_days,
                "start_time": period.start_time.isoformat(),
                "end_time": period.end_time.isoformat(),
                "sensors": sensors,
            })

        # -------------------------------------------------
        # CONTEXTO CLIMÁTICO
        # -------------------------------------------------

        return {
            "context_type": "climate_observation",

            "station_code": analysis.station_code,

            "location": location,

            "reference_time": (
                analysis.reference_time.isoformat()
            ),

            "sampling_interval_minutes": (
                analysis.sampling_interval_minutes
            ),

            "periods": periods,

            "available_climate_variables": (
                self._get_available_variables(analysis)
            ),

            "unavailable_climate_variables": [
                {
                    "variable": "precipitation",
                    "reason": (
                        "No existe un sensor de precipitación "
                        "disponible en la estación."
                    ),
                }
            ],

            "interpretation_guidelines": [
                (
                    "Interpretar las estadísticas considerando "
                    "la cobertura y continuidad temporal."
                ),
                (
                    "No asumir que una cobertura del 100% "
                    "garantiza continuidad de las mediciones."
                ),
                (
                    "No considerar automáticamente inválidos "
                    "los valores iguales a cero."
                ),
                (
                    "No completar ni inferir variables climáticas "
                    "que no estén disponibles."
                ),
                (
                    "No interpretar los promedios como si "
                    "representaran observaciones continuas "
                    "cuando existen brechas temporales."
                ),
            ],
        }

    def _build_sensor_observations(
        self,
        sensor,
    ) -> list[str]:

        observations = []

        if sensor.valid_sample_count == 0:
            observations.append(
                "No existen mediciones válidas para calcular "
                "las estadísticas de este período."
            )

        if sensor.zero_count > 0:
            observations.append(
                f"Se encontraron {sensor.zero_count} mediciones "
                "con valor igual a cero. Requieren revisión; "
                "no se han descartado."
            )

        if sensor.max_gap_minutes is not None:
            observations.append(
                "La mayor brecha temporal detectada entre mediciones fue de "
                f"{sensor.max_gap_minutes:.2f} minutos."
            )

        return observations

    def _get_available_variables(
        self,
        analysis: ClimateAnalysisResponse,
    ) -> list[dict]:

        variables = {}

        for period in analysis.periods:
            for sensor in period.sensors:

                variables[sensor.sensor_code] = {
                    "sensor_code": sensor.sensor_code,
                    "sensor_name": sensor.sensor_name,
                    "unit": sensor.unit,
                }

        return list(variables.values())
