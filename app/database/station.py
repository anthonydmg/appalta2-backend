import time

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.sensor_measurement import get_sensors_by_measurement
from app.models.station import Station
from app.models.station_measurement import StationMeasurement
from app.schemas.station import StationResponse


def get_station_by_station_code(db: Session, station_code: str) -> Station | None:
    return db.query(Station).filter(Station.station_code == station_code).first()


def get_latest_station_measurements(db: Session) -> list[tuple[Station, StationMeasurement | None]]:
    """Cada estación con su medición más reciente (None si nunca envió datos)."""
    latest = (
        db.query(
            StationMeasurement.station_id,
            func.max(StationMeasurement.measurement_timestamp).label("max_timestamp"),
        )
        .group_by(StationMeasurement.station_id)
        .subquery()
    )
    return (
        db.query(Station, StationMeasurement)
        .outerjoin(latest, Station.id == latest.c.station_id)
        .outerjoin(
            StationMeasurement,
            (StationMeasurement.station_id == latest.c.station_id)
            & (StationMeasurement.measurement_timestamp == latest.c.max_timestamp),
        )
        .all()
    )


def get_all_stations(db: Session) -> list[StationResponse]:
    results = get_latest_station_measurements(db)
    sensor_map = get_sensors_by_measurement(db, [m.id for _, m in results if m is not None])
    now = int(time.time())
    return [
        StationResponse.from_orm_rows(station, measurement, sensor_map.get(measurement.id, []) if measurement else [], now)
        for station, measurement in results
    ]
