from typing import Optional

from pydantic import BaseModel, Field, field_validator


class SensorMeasurementRequest(BaseModel):
    sensor_code: str = Field(max_length=100)
    value: float


class StationEventRequest(BaseModel):
    event_type: str
    event_code: Optional[str] = None
    event_data: Optional[str] = None
    message: Optional[str] = None


class StationMeasurementRequest(BaseModel):
    timestamp: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    battery_level: Optional[float] = None
    measurements: list[SensorMeasurementRequest]
    events: Optional[list[StationEventRequest]] = None

    @field_validator("measurements")
    @classmethod
    def validate_measurements(cls, value):
        if not value:
            raise ValueError("Debe enviar al menos una medición")
        return value


# Evento SSE que reciben los clientes suscritos a /stations/stream
class SensorMeasurementEvent(BaseModel):
    sensor_code: str
    value: float


class StationMeasurementEvent(BaseModel):
    station_code: str
    timestamp: int
    latitude: float | None = None
    longitude: float | None = None
    battery_level: float | None = None
    measurements: list[SensorMeasurementEvent]
