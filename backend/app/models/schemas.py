from typing import Literal

from pydantic import BaseModel, Field, computed_field

# The nine NGRBC (National Guidelines on Responsible Business Conduct)
# principles that structure a SEBI BRSR filing's Section C.
NGRBC_PRINCIPLES: dict[int, str] = {
    1: "Ethical, Transparent and Accountable Business Conduct",
    2: "Safety and Sustainability of Goods and Services",
    3: "Employee and Worker Wellbeing",
    4: "Stakeholder Interests",
    5: "Human Rights",
    6: "Environment Protection and Restoration",
    7: "Public and Regulatory Policy Engagement",
    8: "Inclusive Growth and Equitable Development",
    9: "Consumer Value and Responsibility",
}


class PrincipleDisclosure(BaseModel):
    principle: int
    title: str
    essential_indicators_found: int = 0
    essential_indicators_expected: int = 0
    leadership_indicators_found: int = 0
    notes: list[str] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def disclosure_completeness(self) -> float:
        if self.essential_indicators_expected == 0:
            return 0.0
        return round(
            100 * self.essential_indicators_found / self.essential_indicators_expected, 1
        )


class EnvironmentalMetrics(BaseModel):
    scope1_emissions_tco2e: float | None = None
    scope2_emissions_tco2e: float | None = None
    scope3_emissions_tco2e: float | None = None
    total_energy_consumption_gj: float | None = None
    renewable_energy_pct: float | None = None
    water_withdrawal_kl: float | None = None
    water_recycled_pct: float | None = None
    total_waste_generated_mt: float | None = None
    waste_recycled_pct: float | None = None
    revenue_inr_crore: float | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_scope12_emissions(self) -> float | None:
        vals = [v for v in (self.scope1_emissions_tco2e, self.scope2_emissions_tco2e) if v is not None]
        return round(sum(vals), 2) if vals else None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def carbon_intensity_per_revenue(self) -> float | None:
        total = self.total_scope12_emissions
        if total is None or not self.revenue_inr_crore:
            return None
        return round(total / self.revenue_inr_crore, 3)


class GovernanceSignals(BaseModel):
    board_independence_pct: float | None = None
    anti_corruption_policy: bool | None = None
    whistleblower_mechanism: bool | None = None
    complaints_received: int | None = None
    complaints_resolved: int | None = None


class SocialSignals(BaseModel):
    employee_wellbeing_coverage_pct: float | None = None
    safety_incidents_total: int | None = None
    human_rights_complaints: int | None = None
    csr_spend_inr_crore: float | None = None
    women_workforce_pct: float | None = None


class ExtractedBRSRData(BaseModel):
    company_name: str = "Unknown Company"
    sector: str = "Unspecified"
    reporting_year: str | None = None
    principles: list[PrincipleDisclosure] = Field(default_factory=list)
    environment: EnvironmentalMetrics = Field(default_factory=EnvironmentalMetrics)
    governance: GovernanceSignals = Field(default_factory=GovernanceSignals)
    social: SocialSignals = Field(default_factory=SocialSignals)


class DimensionScore(BaseModel):
    dimension: Literal["environmental", "social", "governance"]
    score: float
    max_score: float = 100.0
    rationale: list[str] = Field(default_factory=list)


class ESGScoreResult(BaseModel):
    overall_score: float
    risk_band: Literal["Low", "Moderate", "Elevated", "High"]
    dimensions: list[DimensionScore]
    disclosure_completeness_pct: float


class CarbonBenchmark(BaseModel):
    sector: str
    typical_intensity_range: tuple[float, float]
    unit: str = "tCO2e per INR crore revenue"


class CarbonIntelligenceResult(BaseModel):
    scope1_tco2e: float | None
    scope2_tco2e: float | None
    scope3_tco2e: float | None
    total_scope12_tco2e: float | None
    carbon_intensity_per_revenue: float | None
    renewable_energy_pct: float | None
    benchmark: CarbonBenchmark | None
    benchmark_position: Literal["Below average", "Average", "Above average", "Unknown"]
    observations: list[str] = Field(default_factory=list)


class ReportSummary(BaseModel):
    id: int
    filename: str
    company_name: str
    sector: str
    created_at: str
    extraction_source: str


class ReportDetail(ReportSummary):
    extracted_data: ExtractedBRSRData
    esg_score: ESGScoreResult
    carbon_metrics: CarbonIntelligenceResult


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatMessageOut(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: str


class ChatResponse(BaseModel):
    reply: str
    source: Literal["anthropic", "offline"]
    citations: list[str] = Field(default_factory=list)
