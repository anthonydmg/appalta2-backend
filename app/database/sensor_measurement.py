from sqlalchemy.orm import Session

from app.models.sensor import Sensor
from app.models.sensor_measurement import SensorMeasurement
from app.models.station import Station
from app.models.station_measurement import StationMeasurement
from app.schemas.station import SensorMeasurementResponse


def get_sensor_history(
    db: Session,
    station_code: str,
    sensor_code: str,
    start_time: int | None,
    end_time: int | None,
    limit: int | None,
):
    """Lecturas de un sensor en orden cronológico. Con `limit`, las más recientes."""
    query = (
        db.query(SensorMeasurement.measurement_timestamp, SensorMeasurement.sensor_value)
        .join(StationMeasurement, StationMeasurement.id == SensorMeasurement.measurement_id)
        .join(Station, Station.id == StationMeasurement.station_id)
        .join(Sensor, Sensor.id == SensorMeasurement.sensor_id)
        .filter(Station.station_code == station_code, Sensor.sensor_code == sensor_code)
    )
    if start_time is not None:
        query = query.filter(SensorMeasurement.measurement_timestamp >= start_time)
    if end_time is not None:
        query = query.filter(SensorMeasurement.measurement_timestamp <= end_time)

    if limit is None:
        return query.order_by(SensorMeasurement.measurement_timestamp.asc()).all()
    rows = query.order_by(SensorMeasurement.measurement_timestamp.desc()).limit(limit).all()
    return rows[::-1]


def get_sensors_by_measurement(db: Session, measurement_ids: list[int]) -> dict[int, list[SensorMeasurementResponse]]:
    """Valores de los sensores agrupados por medición, en una sola consulta."""
    if not measurement_ids:
        return {}
    rows = (
        db.query(SensorMeasurement.measurement_id, Sensor.sensor_code, SensorMeasurement.sensor_value)
        .join(Sensor, Sensor.id == SensorMeasurement.sensor_id)
        .filter(SensorMeasurement.measurement_id.in_(measurement_ids))
        .all()
    )
    sensor_map: dict[int, list[SensorMeasurementResponse]] = {}
    for measurement_id, sensor_code, value in rows:
        sensor_map.setdefault(measurement_id, []).append(
            SensorMeasurementResponse(sensor_code=sensor_code, value=float(value))
        )
    return sensor_map
