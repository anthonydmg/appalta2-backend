
from datetime import datetime

from pydantic import BaseModel


class StationLocation(BaseModel):
    latitude: float | None = None
    longitude: float | None = None
    ubigeo: str | None = None
    department: str | None = None
    province: str | None = None
    district: str | None = None


class SensorClimateStatistics(BaseModel):
    sensor_code: str
    sensor_name: str
    unit: str

    mean: float | None
    minimum: float | None
    maximum: float | None

    sample_count: int
    valid_sample_count: int = 0
    expected_count: int
    coverage_percentage: float
    
    zero_count: int

    first_measurement: datetime | None
    last_measurement: datetime | None
    max_gap_minutes: float | None


class ClimatePeriodAnalysis(BaseModel):
    period_days: int
    start_time: datetime
    end_time: datetime
    sensors: list[SensorClimateStatistics]


class ClimateAnalysisResponse(BaseModel):
    station_code: str
    reference_time: datetime
    sampling_interval_minutes: int

    location: StationLocation | None = None

    periods: list[ClimatePeriodAnalysis]
