from sqlalchemy.orm import Session

from app.models.sensor import Sensor
from app.models.sensor_measurement import SensorMeasurement
from app.models.station import Station
from app.models.station_event import StationEvent
from app.models.station_measurement import StationMeasurement
from app.schemas.station_measurement import StationMeasurementRequest


class UnknownSensorError(ValueError):
    pass


def get_sensor_ids(db: Session, sensor_codes: list[str]) -> dict[str, int]:
    rows = db.query(Sensor.sensor_code, Sensor.id).filter(Sensor.sensor_code.in_(sensor_codes)).all()
    return dict(rows)


def save_measurement(db: Session, station: Station, data: StationMeasurementRequest) -> StationMeasurement:
    """Guarda la medición, sus valores por sensor y sus eventos en una sola transacción."""
    sensor_ids = get_sensor_ids(db, [m.sensor_code for m in data.measurements])
    unknown = sorted({m.sensor_code for m in data.measurements} - sensor_ids.keys())
    if unknown:
        raise UnknownSensorError(f"Sensores no registrados: {', '.join(unknown)}")

    measurement = StationMeasurement(
        station_id=station.id,
        measurement_timestamp=data.timestamp,
        latitude=data.latitude,
        longitude=data.longitude,
        battery_level=data.battery_level,
    )
    db.add(measurement)
    db.flush()  # obtiene measurement.id sin hacer commit

    db.add_all(
        SensorMeasurement(
            measurement_id=measurement.id,
            sensor_id=sensor_ids[sensor.sensor_code],
            measurement_timestamp=data.timestamp,
            sensor_value=sensor.value,
        )
        for sensor in data.measurements
    )
    db.add_all(
        StationEvent(
            station_id=station.id,
            measurement_id=measurement.id,
            event_timestamp=data.timestamp,
            event_type=event.event_type,
            event_message=event.message,
        )
        for event in data.events or []
    )
    station.last_timestamp = data.timestamp
    db.commit()
    return measurement


def get_latest_station_measurement(db: Session, station_code: str):
    """(estación, su medición más reciente o None); None si la estación no existe."""
    return (
        db.query(Station, StationMeasurement)
        .outerjoin(StationMeasurement, StationMeasurement.station_id == Station.id)
        .filter(Station.station_code == station_code)
        .order_by(StationMeasurement.measurement_timestamp.desc())
        .first()
    )
