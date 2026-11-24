
from datetime import datetime, timezone, timedelta

from app.repositories.climate_repository import ClimateRepository
from app.schemas.climate_analysis import (
    ClimateAnalysisResponse,
    ClimatePeriodAnalysis,
    SensorClimateStatistics,
    StationLocation,
)


class ClimateAnalysisService:

    SAMPLING_INTERVAL_MINUTES = 20

    def __init__(self, db):
        self.repository = ClimateRepository(db)

    def analyze(
        self,
        station_code: str,
        reference_time: datetime | None = None,
    ) -> ClimateAnalysisResponse:

        if reference_time is None:
            reference_time = datetime.now(timezone.utc)

        if reference_time.tzinfo is None:
            raise ValueError(
                "reference_time debe incluir zona horaria"
            )

        rows = self.repository.get_climate_statistics(
            station_code=station_code,
            reference_time=reference_time,
        )

        # -------------------------------------------------
        # UBICACIÓN DE LA ESTACIÓN
        # -------------------------------------------------

        location = None

        if rows:
            first_row = rows[0]

            location = StationLocation(
                latitude=first_row["latitude"],
                longitude=first_row["longitude"],
                ubigeo=first_row["ubigeo"],
                department=first_row["department"],
                province=first_row["province"],
                district=first_row["district"],
            )

        # -------------------------------------------------
        # ESTADÍSTICAS CLIMÁTICAS
        # -------------------------------------------------

        periods_map = {}

        for row in rows:

            days = row["period_days"]

            if days not in periods_map:
                periods_map[days] = []

            periods_map[days].append(
                SensorClimateStatistics(
                    sensor_code=row["sensor_code"],
                    sensor_name=row["sensor_name"],
                    unit=row["unit"],

                    mean=(
                        float(row["mean"])
                        if row["mean"] is not None
                        else None
                    ),

                    minimum=(
                        float(row["minimum"])
                        if row["minimum"] is not None
                        else None
                    ),

                    maximum=(
                        float(row["maximum"])
                        if row["maximum"] is not None
                        else None
                    ),

                    sample_count=row["sample_count"],
                    expected_count=row["expected_count"],
                    coverage_percentage=float(
                        row["coverage_percentage"]
                    ),

                    zero_count=row["zero_count"],

                    first_measurement=row["first_measurement"],
                    last_measurement=row["last_measurement"],

                    max_gap_minutes=(
                        float(row["max_gap_minutes"])
                        if row["max_gap_minutes"] is not None
                        else None
                    )
                )
            )

        # -------------------------------------------------
        # CONSTRUCCIÓN DE PERÍODOS
        # -------------------------------------------------

        periods = []

        for days in [7, 15, 30]:

            periods.append(
                ClimatePeriodAnalysis(
                    period_days=days,
                    start_time=reference_time - timedelta(days=days),
                    end_time=reference_time,
                    sensors=periods_map.get(days, []),
                )
            )

        # -------------------------------------------------
        # RESPUESTA
        # -------------------------------------------------

        return ClimateAnalysisResponse(
            station_code=station_code,
            reference_time=reference_time,
            sampling_interval_minutes=self.SAMPLING_INTERVAL_MINUTES,
            location=location,
            periods=periods,
        )
