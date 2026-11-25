from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CropFieldCreate(BaseModel):
    field_code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=100)

    department: str = Field(min_length=1, max_length=100)
    province: str = Field(min_length=1, max_length=100)
    district: str = Field(min_length=1, max_length=100)

    crop_common_name: str = Field(
        default="Palto",
        max_length=50,
    )
    crop_scientific_name: str = Field(
        default="Persea americana",
        max_length=100,
    )
    crop_variety: str = Field(
        default="Hass",
        max_length=50,
    )

class CropFieldResponse(CropFieldCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)