from app.models.schemas import (
    EnvironmentalMetrics,
    ExtractedBRSRData,
    GovernanceSignals,
    PrincipleDisclosure,
    SocialSignals,
)
from app.services import brsr_extractor, esg_scoring, pdf_parser


def test_scores_are_within_bounds(sample_text):
    normalized = pdf_parser.normalize_whitespace(sample_text)
    data = brsr_extractor.extract_structured_data(normalized)
    result = esg_scoring.compute_esg_score(data)

    assert 0 <= result.overall_score <= 100
    assert result.risk_band in {"Low", "Moderate", "Elevated", "High"}
    assert len(result.dimensions) == 3
    for dim in result.dimensions:
        assert 0 <= dim.score <= 100
        assert dim.rationale, f"{dim.dimension} produced no rationale"


def test_fully_disclosed_strong_company_scores_low_risk():
    principles = [
        PrincipleDisclosure(
            principle=n,
            title=f"P{n}",
            essential_indicators_found=10,
            essential_indicators_expected=10,
        )
        for n in range(1, 10)
    ]
    data = ExtractedBRSRData(
        company_name="Model Corp",
        sector="Manufacturing",
        principles=principles,
        environment=EnvironmentalMetrics(
            scope1_emissions_tco2e=100,
            scope2_emissions_tco2e=50,
            revenue_inr_crore=1000,
            renewable_energy_pct=90,
            water_recycled_pct=80,
            waste_recycled_pct=85,
        ),
        governance=GovernanceSignals(
            board_independence_pct=80,
            anti_corruption_policy=True,
            whistleblower_mechanism=True,
            complaints_received=5,
            complaints_resolved=5,
        ),
        social=SocialSignals(
            safety_incidents_total=0,
            csr_spend_inr_crore=10,
            women_workforce_pct=40,
            human_rights_complaints=0,
        ),
    )
    result = esg_scoring.compute_esg_score(data)
    assert result.overall_score >= 75
    assert result.risk_band == "Low"


def test_empty_disclosure_scores_high_risk():
    principles = [
        PrincipleDisclosure(principle=n, title=f"P{n}", essential_indicators_found=0, essential_indicators_expected=10)
        for n in range(1, 10)
    ]
    data = ExtractedBRSRData(principles=principles)
    result = esg_scoring.compute_esg_score(data)
    assert result.overall_score < 40
    assert result.risk_band == "High"
