
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ClimateMeasurement(BaseModel):
    timestamp: datetime
    sensor_code: str
    sensor_name: str
    value: float
    unit: str


class ClimateDataResponse(BaseModel):
    station_code: str
    start_time: datetime
    end_time: datetime
    total_measurements: int
    measurements: list[ClimateMeasurement]
