from app.services import brsr_extractor, pdf_parser


def _extract(sample_text: str):
    normalized = pdf_parser.normalize_whitespace(sample_text)
    return brsr_extractor.extract_structured_data(normalized)


def test_company_meta(sample_text):
    data = _extract(sample_text)
    assert data.company_name == "Greenfield Textiles Limited"
    assert data.sector == "Textiles"
    assert data.reporting_year == "2023-24"


def test_environmental_fields(sample_text):
    data = _extract(sample_text)
    env = data.environment
    assert env.scope1_emissions_tco2e == 12500.0
    assert env.scope2_emissions_tco2e == 8200.0
    assert env.scope3_emissions_tco2e is None
    assert env.renewable_energy_pct == 18.0
    assert env.revenue_inr_crore == 4250.0
    assert env.total_scope12_emissions == 20700.0
    assert env.carbon_intensity_per_revenue == round(20700.0 / 4250.0, 3)


def test_governance_fields(sample_text):
    data = _extract(sample_text)
    gov = data.governance
    assert gov.anti_corruption_policy is True
    assert gov.whistleblower_mechanism is True
    assert gov.complaints_received == 12
    assert gov.complaints_resolved == 11


def test_social_fields(sample_text):
    data = _extract(sample_text)
    social = data.social
    assert social.safety_incidents_total == 3
    assert social.csr_spend_inr_crore == 18.0
    assert social.women_workforce_pct == 28.0
    assert social.human_rights_complaints == 1


def test_all_nine_principles_present(sample_text):
    data = _extract(sample_text)
    assert len(data.principles) == 9
    assert {p.principle for p in data.principles} == set(range(1, 10))
    for p in data.principles:
        assert p.essential_indicators_found > 0, f"Principle {p.principle} found nothing"
        assert 0 <= p.disclosure_completeness <= 100


def test_missing_fields_are_none_not_guessed():
    data = brsr_extractor.extract_structured_data("This document has no BRSR content at all.")
    assert data.environment.scope1_emissions_tco2e is None
    assert data.governance.anti_corruption_policy is None
    assert data.company_name == "Unknown Company"
