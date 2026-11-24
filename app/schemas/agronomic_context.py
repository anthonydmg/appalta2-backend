
from pydantic import BaseModel, Field


class DetectedPest(BaseModel):
    scientific_name: str
    common_name: str | None = None

    confidence: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )

    affected_leaf_side: str | None = None


class DetectedDamage(BaseModel):
    damage_name: str

    description: str | None = None

    confidence: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )


class VisionDiagnosisInput(BaseModel):
    diagnosis_id: int | None = None

    station_code: str

    detected_pests: list[DetectedPest] = Field(
        default_factory=list
    )

    detected_damages: list[DetectedDamage] = Field(
        default_factory=list
    )
