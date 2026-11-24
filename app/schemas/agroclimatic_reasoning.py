
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class DiagnosisSummary(BaseModel):
    scientific_name: str
    common_name: str | None = None
    confidence: float | None = None
    affected_leaf_side: str | None = None


class ClimateObservation(BaseModel):
    period_days: int
    variable: str
    mean: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    unit: str
    interpretation: str


class ScientificFinding(BaseModel):
    evidence_code: str
    finding: str
    relevance_to_current_conditions: str
    validation_status: str


class AgroclimaticAssessment(BaseModel):
    assessment: str
    evidence_strength: Literal[
        "strong",
        "moderate",
        "limited",
        "insufficient"
    ]
    causal_relationship_established: bool = False
    justification: str


class ReportBaseModel(BaseModel):
    model_config = {
        "extra": "forbid",
        "validate_assignment": True
    }


class EvaluationCategory(str, Enum):
    ROUTINE_SURVEILLANCE = "routine_surveillance"
    REINFORCED_SURVEILLANCE = "reinforced_surveillance"
    PRIORITY_PHYTOSANITARY_SURVEILLANCE = (
        "priority_phytosanitary_surveillance"
    )
    FIELD_TECHNICAL_EVALUATION = "field_technical_evaluation"


class DiagnosisSummary(BaseModel):
    scientific_name: str
    common_name: str | None = None
    confidence: float | None = None
    affected_leaf_side: str | None = None


class ClimateObservation(BaseModel):
    period_days: int
    variable: str
    mean: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    unit: str
    interpretation: str


class ScientificFinding(BaseModel):
    evidence_code: str
    finding: str
    relevance_to_current_conditions: str
    validation_status: str


class AgroclimaticAssessment(BaseModel):
    assessment: str
    evidence_strength: Literal[
        "strong",
        "moderate",
        "limited",
        "insufficient"
    ]
    causal_relationship_established: bool = False
    justification: str


class AgronomicRecommendation(BaseModel):
    action: str
    justification: str
    recommendation_type: Literal[
        "monitoring",
        "preventive",
        "management"
    ]
    scientific_support: Literal[
        "direct",
        "indirect",
        "expert_precaution",
        "not_established"
    ]


class DataLimitation(BaseModel):
    variable: str | None = None
    limitation: str
    impact_on_interpretation: str


# Interpretación climática generada por Gemma.
class ClimateInterpretation(BaseModel):
    period_days: int
    sensor_code: str
    interpretation: str


# Relevancia de la evidencia generada por Gemma.
class ScientificFindingInterpretation(BaseModel):
    scientific_name: str
    evidence_code: str
    relevance_to_current_conditions: str


# Respuesta exclusiva de Gemma.
class AgroclimaticReasoningResponse(BaseModel):

    climate_interpretations: list[ClimateInterpretation] = Field(
        default_factory=list
    )

    scientific_findings: list[ScientificFindingInterpretation] = Field(
        default_factory=list
    )

    scientific_evidence: str

    seasonal_geographic_context: str

    agroclimatic_assessment: AgroclimaticAssessment

    recommendations: list[AgronomicRecommendation] = Field(
        default_factory=list
    )

    limitations: list[DataLimitation] = Field(
        default_factory=list
    )

    overall_conclusion: str
