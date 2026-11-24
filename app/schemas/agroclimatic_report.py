
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.agroclimatic_reasoning import AgroclimaticAssessment, AgronomicRecommendation, ClimateObservation, DataLimitation


class ReportBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )


class ValidationStatus(str, Enum):
    EXTRACTED_PENDING_AGRONOMIC_VALIDATION = (
        "EXTRACTED_PENDING_AGRONOMIC_VALIDATION"
    )
    AGRONOMICALLY_VALIDATED = "AGRONOMICALLY_VALIDATED"


class EvidenceStrength(str, Enum):
    LIMITED = "limited"
    MODERATE = "moderate"
    STRONG = "strong"
    INSUFFICIENT = "insufficient"


class RecommendationType(str, Enum):
    MONITORING = "monitoring"
    PREVENTIVE = "preventive"
    MANAGEMENT = "management"
    FIELD_VERIFICATION = "field_verification"


class RecommendationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EvaluationCategory(str, Enum):
    ROUTINE_SURVEILLANCE = "routine_surveillance"
    REINFORCED_SURVEILLANCE = "reinforced_surveillance"
    PRIORITY_PHYTOSANITARY_SURVEILLANCE = (
        "priority_phytosanitary_surveillance"
    )
    FIELD_TECHNICAL_EVALUATION = "field_technical_evaluation"


class ClimateIndicator(ReportBaseModel):
    variable: str
    label: str

    mean: float | None = None
    minimum: float | None = None
    maximum: float | None = None

    unit: str


class ClimateDataQuality(ReportBaseModel):
    status: str | None = None

    sample_count: int = 0
    valid_sample_count: int = 0
    expected_count: int = 0

    coverage_percentage: float | None = None
    max_gap_minutes: float | None = None

    observations: list[str] = Field(default_factory=list)


class EvidenceReference(ReportBaseModel):
    evidence_code: str
    study_code: str

    validation_status: ValidationStatus


class StudyConditions(ReportBaseModel):
    temperature: float | None = None
    temperature_unit: str | None = None

    relative_humidity: float | None = None
    relative_humidity_unit: str | None = None

    other_conditions: list[str] = Field(default_factory=list)


class GeographicLocation(ReportBaseModel):
    district: str | None = None
    province: str | None = None
    department: str | None = None
    country: str | None = None



class ClimatePeriod(ReportBaseModel):
    period_days: int

    indicators: list[ClimateIndicator] = Field(
        default_factory=list
    )

    data_quality: list[ClimateDataQuality] = Field(
        default_factory=list
    )


class ClimateConditionsSection(ReportBaseModel):
    section_id: str = "climate_conditions"
    title: str = "Condiciones climáticas recientes"

    summary: str

    primary_period_days: int = 7

    indicators: list[ClimateIndicator] = Field(
        default_factory=list
    )

    additional_periods: list[ClimatePeriod] = Field(
        default_factory=list
    )

    data_quality_observations: list[str] = Field(
        default_factory=list
    )



class ScientificFinding(ReportBaseModel):
    reference: EvidenceReference

    finding: str

    result_value: float | None = None
    result_unit: str | None = None

    study_type: str | None = None
    study_location: GeographicLocation | None = None

    conditions: StudyConditions | None = None

    relevance_to_current_conditions: str | None = None


class ScientificEvidenceSection(ReportBaseModel):
    section_id: str = "scientific_evidence"
    title: str = (
        "Evidencia científica y desarrollo de la plaga"
    )

    introduction: str

    findings: list[ScientificFinding] = Field(
        default_factory=list
    )

    interpretation: str

    caveats: list[str] = Field(
        default_factory=list
    )



class SeasonalPattern(ReportBaseModel):
    reference: EvidenceReference

    pattern_type: str

    finding: str

    months: list[int] = Field(
        default_factory=list
    )

    current_month_matches: bool

    study_location: GeographicLocation | None = None


class SeasonalGeographicSection(ReportBaseModel):
    section_id: str = "seasonal_geographic_context"
    title: str = "Contexto estacional y geográfico"

    introduction: str

    patterns: list[SeasonalPattern] = Field(
        default_factory=list
    )

    interpretation: str

    geographic_limitation: str | None = None




class AgroclimaticAssessmentSection(ReportBaseModel):
    section_id: str = "agroclimatic_assessment"
    title: str = "Evaluación agroclimática"

    assessment: str

    evidence_references: list[str] = Field(
        default_factory=list
    )

    evidence_strength: EvidenceStrength

    causal_relationship_established: bool

    field_verification_required: bool = True

    justification: str

    evaluation_category: EvaluationCategory

    evaluation_label: str

    evaluation_explanation: str



class RecommendationSupport(ReportBaseModel):
    support_type: str

    evidence_references: list[str] = Field(
        default_factory=list
    )

    explanation: str | None = None


class Recommendation(ReportBaseModel):
    recommendation_id: str

    action: str
    purpose: str

    recommendation_type: RecommendationType

    priority: RecommendationPriority

    support: RecommendationSupport


class RecommendationsSection(ReportBaseModel):
    section_id: str = "recommendations"
    title: str = "Recomendaciones"

    introduction: str | None = None

    items: list[Recommendation] = Field(
        default_factory=list
    )



class ReportLimitation(ReportBaseModel):
    limitation_code: str

    category: str

    description: str

    impact: str

    evidence_references: list[str] = Field(
        default_factory=list
    )


class LimitationsSection(ReportBaseModel):
    section_id: str = "limitations"
    title: str = "Limitaciones"

    items: list[ReportLimitation] = Field(
        default_factory=list
    )



class EvaluationResultSection(ReportBaseModel):
    section_id: str = "evaluation_result"
    title: str = "Resultado de la evaluación"

    category: EvaluationCategory

    label: str

    explanation: str

    requires_field_verification: bool = True


class AgroclimaticReport(BaseModel):

    # 1. Condiciones climáticas recientes
    climate_conditions: list[ClimateObservation] = Field(
        default_factory=list
    )

    # 2. Evidencia científica
    scientific_evidence: str

    # 3. Contexto estacional y geográfico
    seasonal_geographic_context: str

    # 4. Evaluación agroclimática
    agroclimatic_assessment: AgroclimaticAssessment

    # 5. Recomendaciones
    recommendations: list[AgronomicRecommendation] = Field(
        default_factory=list
    )

    # 6. Limitaciones
    limitations: list[DataLimitation] = Field(
        default_factory=list
    )

    # Conclusión general
    overall_conclusion: str