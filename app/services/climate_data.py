
from datetime import datetime, timezone

from sqlalchemy import text, bindparam
from sqlalchemy.orm import Session

from app.schemas.climate_data import (
    ClimateDataResponse,
    ClimateMeasurement,
)


class ClimateDataService:

    def __init__(self, db: Session):
        self.db = db

    def get_measurements(
        self,
        station_code: str,
        start_time: datetime,
        end_time: datetime,
        sensor_codes: list[str] | None = None,
        limit: int = 10000,
    ) -> ClimateDataResponse:

        # Validar intervalo temporal
        if start_time.tzinfo is None or end_time.tzinfo is None:
            raise ValueError(
                "start_time y end_time deben incluir zona horaria"
            )

        if start_time >= end_time:
            raise ValueError(
                "start_time debe ser anterior a end_time"
            )

        if sensor_codes is not None and not sensor_codes:
            raise ValueError(
                "sensor_codes no puede ser una lista vacía"
            )

        # Convertir a timestamp Unix en segundos
        start_timestamp = int(start_time.timestamp())
        end_timestamp = int(end_time.timestamp())

        query = """
            SELECT
                st.station_code,
                stm.measurement_timestamp,
                s.sensor_code,
                s.sensor_name,
                s.unit,
                sm.sensor_value

            FROM station_measurements stm

            INNER JOIN stations st
                ON st.id = stm.station_id

            INNER JOIN sensor_measurements sm
                ON sm.measurement_id = stm.id

            INNER JOIN sensors s
                ON s.id = sm.sensor_id

            WHERE st.station_code = :station_code

              AND stm.measurement_timestamp >= :start_timestamp
              AND stm.measurement_timestamp < :end_timestamp
        """

        params = {
            "station_code": station_code,
            "start_timestamp": start_timestamp,
            "end_timestamp": end_timestamp,
            "limit": limit,
        }

        # Filtro opcional por sensores
        if sensor_codes is not None:
            query += """
                AND s.sensor_code IN :sensor_codes
            """
            params["sensor_codes"] = sensor_codes

        query += """
            ORDER BY
                stm.measurement_timestamp ASC,
                s.sensor_code ASC

            LIMIT :limit
        """

        statement = text(query)

        if sensor_codes is not None:
            statement = statement.bindparams(
                bindparam("sensor_codes", expanding=True)
            )

        result = self.db.execute(statement, params)

        rows = result.mappings().all()

        measurements = []

        for row in rows:
            timestamp = datetime.fromtimestamp(
                row["measurement_timestamp"],
                tz=timezone.utc,
            )

            measurements.append(
                ClimateMeasurement(
                    timestamp=timestamp,
                    sensor_code=row["sensor_code"],
                    sensor_name=row["sensor_name"],
                    value=float(row["sensor_value"]),
                    unit=row["unit"],
                )
            )

        return ClimateDataResponse(
            station_code=station_code,
            start_time=start_time,
            end_time=end_time,
            total_measurements=len(measurements),
            measurements=measurements,
        )
