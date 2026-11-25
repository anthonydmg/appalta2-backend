from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FieldMappingCreate(BaseModel):
    uuid_local: UUID

    field_mapping_id: str = Field(min_length=1, max_length=100)
    field_mapping_name: str = Field(min_length=1, max_length=100)

    flight_date: date
    field_id: int


class FieldMappingResponse(BaseModel):
    id: int
    uuid_local: UUID
    field_mapping_id: str
    field_mapping_name: str
    flight_date: date
    field_id: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)