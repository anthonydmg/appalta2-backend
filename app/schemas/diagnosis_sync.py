from datetime import datetime
from typing import Optional, Literal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class DetectedLeafConditionSyncItem(BaseModel):
    id_class_model: int

    probability: float = Field(
        ge=0,
        le=1
    )


class DiagnosisSyncItem(BaseModel):
    diagnosis_client_uuid: UUID
    image_client_uuid: UUID

    created_date: datetime
    captured_at: datetime

    side_leaf: Literal["haz", "enves"]

    latitude: Optional[float] = Field(
        default=None,
        ge=-90,
        le=90
    )

    longitude: Optional[float] = Field(
        default=None,
        ge=-180,
        le=180
    )

    detected_leaf_conditions: list[DetectedLeafConditionSyncItem] = Field(
        default_factory=list,
        max_length=100
    )


class DiagnosesSyncRequest(BaseModel):
    diagnoses: list[DiagnosisSyncItem] = Field(
        min_length=1,
        max_length=5
    )


class DiagnosisSyncResult(BaseModel):
    diagnosis_client_uuid: UUID
    image_client_uuid: UUID

    status: Literal["SYNCED", "ERROR"]

    id_diagnosis: Optional[int] = None
    id_image: Optional[int] = None

    message: str


class MetadataSyncItemResult(BaseModel):
    diagnosis_client_uuid: UUID
    image_client_uuid: UUID
    status: Literal["METADATA_SYNCED", "SYNCED", "ERROR"]
    image_status: Literal["PENDING", "UPLOADED", "UNKNOWN"]
    id_diagnosis: int | None = None
    id_image: int | None = None
    message: str

class DiagnosesSyncResponse(BaseModel):
    total_received: int
    total_registered: int
    total_failed: int
    results: list[MetadataSyncItemResult]



class MetadataSyncItemResult(BaseModel):
    diagnosis_client_uuid: UUID
    image_client_uuid: UUID
    status: Literal["METADATA_SYNCED", "SYNCED", "ERROR"]
    image_status: Literal["PENDING", "UPLOADED", "UNKNOWN"]
    id_diagnosis: int | None = None
    id_image: int | None = None
    message: str

class OptimizedImageUploadResponse(BaseModel):
    image_client_uuid: UUID
    image_status: Literal["UPLOADED"]
    diagnosis_status: Literal["SYNCED"]
    id_image: int
    id_diagnosis: int
    storage_path: str
    message: str


class DiagnosisSyncStatusResponse(BaseModel):
    diagnosis_client_uuid: UUID
    image_client_uuid: UUID
    status: Literal["METADATA_SYNCED", "SYNCED"]
    metadata_status: Literal["REGISTERED"]
    optimized_image_status: Literal["PENDING", "UPLOADED"]
    original_image_status: Literal["NOT_UPLOADED", "PENDING", "UPLOADED"]
    is_fully_synced: bool
    pending_items: list[str]


class OptimizedImageBatchItemResult(BaseModel):
    image_client_uuid: UUID
    status: Literal["UPLOADED", "ERROR"]
    diagnosis_status: Literal["SYNCED", "METADATA_SYNCED", "UNKNOWN"]
    id_image: int | None = None
    id_diagnosis: int | None = None
    storage_path: str | None = None
    message: str


class OptimizedImageBatchResponse(BaseModel):
    total_received: int
    total_uploaded: int
    total_failed: int
    results: list[OptimizedImageBatchItemResult]

