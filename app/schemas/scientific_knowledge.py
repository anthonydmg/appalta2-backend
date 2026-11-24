
from typing import Any, Optional

from pydantic import BaseModel, Field


class ScientificEvidenceQuery(BaseModel):
    scientific_name: Optional[str] = None
    climate_variable: Optional[str] = None
    biological_response: Optional[str] = None
    location: Optional[str] = None
    study_type: Optional[str] = None
    validation_status: Optional[str] = None


class ScientificEvidenceItem(BaseModel):
    evidence_code: str
    scientific_name: str
    document_code: str

    source_title: Optional[str] = None
    authors: Optional[list[str]] = None
    publication_year: Optional[int] = None

    study_type: Optional[str] = None
    study_location: Optional[str] = None

    # Todas las ubicaciones del estudio
    study_locations: list[dict[str, Any]] = Field(
        default_factory=list
    )

    # Solo las ubicaciones que coincidieron con la búsqueda
    matched_locations: list[dict[str, Any]] = Field(
        default_factory=list
    )

    climate_variable: Optional[str] = None
    biological_response: Optional[str] = None
    finding: Optional[str] = None

    # Información JSONB
    conditions: Any = Field(default_factory=dict)
    result: Any = Field(default_factory=dict)
    source_location: Any = None

    evidence_type: Optional[str] = None
    statistical_support: Optional[str] = None
    interpretation_limit: Optional[str] = None
    validation_status: Optional[str] = None


class ScientificRetrievalMetadata(BaseModel):
    total_evidences: int
    limit: int
    has_results: bool


class ScientificEvidenceSearchResponse(BaseModel):
    query: ScientificEvidenceQuery
    retrieval: ScientificRetrievalMetadata
    evidence: list[ScientificEvidenceItem] = Field(
        default_factory=list
    )


class ScientificQuestionRequest(BaseModel):

    question: str = Field(
        min_length=5,
        max_length=3000
    )

    scientific_name: str | None = None

    climate_variable: str | None = None

    biological_response: str | None = None

    location: str | None = None

    study_type: str | None = None

    validation_status: str | None = None

    limit: int = Field(
        default=20,
        ge=1,
        le=100
    )


class ScientificReference(BaseModel):

    evidence_code: str
    document_code: str

    source_title: str | None = None

    publication_year: int | None = None

    source_location: dict | list | str | None = None

    matched_locations: list[dict] = Field(
        default_factory=list
    )

    validation_status: str | None = None


class ScientificQuestionResponse(BaseModel):

    question: str

    answer: str

    retrieval: dict

    references: list[ScientificReference]

    model: str | None = None