
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session


class ClimateRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_climate_statistics(
        self,
        station_code: str,
        reference_time: datetime,
    ) -> list[dict]:

        if reference_time.tzinfo is None:
            raise ValueError(
                "reference_time debe incluir zona horaria"
            )

        reference_timestamp = int(reference_time.timestamp())

        query = text("""
            WITH periods AS (
                SELECT
                    period_days,
                    :reference_timestamp - (period_days * 86400)
                        AS start_timestamp,
                    :reference_timestamp AS end_timestamp
                FROM (
                    VALUES (7), (15), (30)
                ) AS p(period_days)
            ),

            station_info AS (
                SELECT
                    s.id,
                    s.station_code,
                    s.latitude,
                    s.longitude,
                    s.ubigeo,

                    d.nombdep AS department,
                    d.nombprov AS province,
                    d.nombdist AS district

                FROM stations s

                LEFT JOIN geography.districts d
                    ON d.ubigeo = s.ubigeo

                WHERE s.station_code = :station_code
            ),

            station_sensor_catalog AS (
                SELECT
                    s.id AS sensor_id,
                    s.sensor_code,
                    s.sensor_name,
                    s.unit

                FROM station_info st

                JOIN station_sensors ss
                    ON ss.station_id = st.id

                JOIN sensors s
                    ON s.id = ss.sensor_id
            )

            SELECT
                :station_code AS station_code,

                -- Ubicación de la estación
                st.latitude,
                st.longitude,
                st.ubigeo,
                st.department,
                st.province,
                st.district,

                p.period_days,

                c.sensor_id,
                c.sensor_code,
                c.sensor_name,
                c.unit,

                COALESCE(a.sample_count, 0) AS sample_count,
                COALESCE(a.valid_sample_count, 0) AS valid_sample_count,

                a.mean,
                a.minimum,
                a.maximum,

                a.first_measurement,
                a.last_measurement,
                a.max_gap_minutes,

                COALESCE(a.zero_count, 0) AS zero_count,

                CEIL(
                    (p.period_days * 86400.0) / 1200.0
                )::INTEGER AS expected_count,

                ROUND(
                    LEAST(
                        COALESCE(a.sample_count, 0) * 100.0 /
                        NULLIF(
                            CEIL((p.period_days * 86400.0) / 1200.0),
                            0
                        ),
                        100.0
                    ),
                    2
                ) AS received_coverage_percentage,

                ROUND(
                    LEAST(
                        COALESCE(a.valid_sample_count, 0) * 100.0 /
                        NULLIF(
                            CEIL(
                                (p.period_days * 86400.0) / 1200.0
                            ),
                            0
                        ),
                        100.0
                    ),
                    2
                ) AS coverage_percentage

            FROM periods p

            CROSS JOIN station_sensor_catalog c

            CROSS JOIN station_info st

           LEFT JOIN LATERAL (
                WITH ordered_measurements AS (
                    SELECT
                        sm.sensor_value,
                        stm.measurement_timestamp

                    FROM station_info st

                    JOIN station_measurements stm
                        ON stm.station_id = st.id

                    JOIN sensor_measurements sm
                        ON sm.measurement_id = stm.id

                    WHERE sm.sensor_id = c.sensor_id
                    AND stm.measurement_timestamp >= p.start_timestamp
                    AND stm.measurement_timestamp < p.end_timestamp
                ),

                valid_measurements AS (
                    SELECT
                        sensor_value,
                        measurement_timestamp,

                        measurement_timestamp -
                        LAG(measurement_timestamp) OVER (
                            ORDER BY measurement_timestamp
                        ) AS gap_seconds

                    FROM ordered_measurements
                    WHERE sensor_value <> 0
                )

                SELECT
                    -- Todas las mediciones recibidas
                    (
                        SELECT COUNT(*)
                        FROM ordered_measurements
                    )::INTEGER AS sample_count,

                    -- Mediciones válidas
                    COUNT(*)::INTEGER AS valid_sample_count,

                    -- Estadísticas sin ceros
                    AVG(sensor_value) AS mean,
                    MIN(sensor_value) AS minimum,
                    MAX(sensor_value) AS maximum,

                    -- Primera y última medición válida
                    TO_TIMESTAMP(
                        MIN(measurement_timestamp)
                    ) AS first_measurement,

                    TO_TIMESTAMP(
                        MAX(measurement_timestamp)
                    ) AS last_measurement,

                    -- Mayor brecha entre mediciones válidas
                    CASE
                        WHEN COUNT(*) = 0 THEN
                            (p.end_timestamp - p.start_timestamp) / 60.0

                        ELSE
                            GREATEST(
                                COALESCE(MAX(gap_seconds), 0),

                                MIN(measurement_timestamp)
                                    - p.start_timestamp,

                                p.end_timestamp
                                    - MAX(measurement_timestamp)
                            ) / 60.0
                    END AS max_gap_minutes,

                    -- Mediciones iguales a cero
                    (
                        SELECT COUNT(*)
                        FROM ordered_measurements
                        WHERE sensor_value = 0
                    )::INTEGER AS zero_count

                FROM valid_measurements

            ) a ON TRUE

            ORDER BY
                p.period_days,
                c.sensor_code;
        """)

        result = self.db.execute(
            query,
            {
                "station_code": station_code,
                "reference_timestamp": reference_timestamp,
            },
        )

        return [
            dict(row)
            for row in result.mappings().all()
        ]


def build_quality_observations(
    zero_count: int,
    max_gap_minutes: float | None,
) -> list[str]:

    observations = []

    if zero_count > 0:
        observations.append(
            f"Se encontraron {zero_count} mediciones "
            "con valor igual a cero. Requieren revisión."
        )

    if max_gap_minutes is not None:
        observations.append(
            f"La mayor brecha temporal fue de "
            f"{max_gap_minutes / 60:.2f} horas."
        )

    return observations
