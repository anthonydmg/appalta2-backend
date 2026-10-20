import time
from typing import Optional

from pydantic import BaseModel

from app.config.constants import ONLINE_TIMEOUT


def _to_float(value) -> Optional[float]:
    return None if value is None else float(value)


class SensorMeasurementResponse(BaseModel):
    sensor_code: str
    value: float


class StationResponse(BaseModel):
    station_code: str
    name: str
    online: bool
    measurement_timestamp: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    battery_level: Optional[float] = None
    measurements: list[SensorMeasurementResponse] = []

    @classmethod
    def from_orm_rows(cls, station, measurement, sensors: list[SensorMeasurementResponse], now: int | None = None):
        """Arma la respuesta desde la estación y su última medición (None si nunca envió datos)."""
        if measurement is None:
            return cls(station_code=station.station_code, name=station.name, online=False)
        now = int(time.time()) if now is None else now
        return cls(
            station_code=station.station_code,
            name=station.name,
            online=(now - measurement.measurement_timestamp) <= ONLINE_TIMEOUT,
            measurement_timestamp=measurement.measurement_timestamp,
            latitude=_to_float(measurement.latitude),
            longitude=_to_float(measurement.longitude),
            battery_level=_to_float(measurement.battery_level),
            measurements=sensors,
        )
