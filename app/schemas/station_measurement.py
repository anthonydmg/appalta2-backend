from pydantic import BaseModel, model_validator
from typing import Optional


class SensorMeasurementRequest(BaseModel):

    sensor_code: str

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

    events: Optional[
        list[StationEventRequest]
    ] = None

    @model_validator(mode="after")
    def validate_measurements(self):

        if len(self.measurements) == 0:
            raise ValueError(
                "Debe enviar al menos una medición"
            )

        return self
    
class SensorMeasurementEvent(BaseModel):

    sensor_code: str

    value: float


class StationEvent(BaseModel):

    event_type: str

    message: str


class StationMeasurementEvent(BaseModel):

    station_code: str

    timestamp: int

    latitude: float | None = None

    longitude: float | None = None

    battery_level: float | None = None

    measurements: list[SensorMeasurementEvent]
