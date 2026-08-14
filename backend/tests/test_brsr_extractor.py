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


def test_real_brsr_report_is_valid(sample_text):
    normalized = pdf_parser.normalize_whitespace(sample_text)
    is_valid, reason = brsr_extractor.assess_brsr_validity(normalized)
    assert is_valid is True
    assert reason is None


def test_unrelated_document_is_rejected():
    resume_text = """
    JOHN DOE — Software Engineer

    EXPERIENCE
    Senior Developer at TechCorp, 2020-2024
    Built scalable web applications and led a team of 5 engineers.

    EDUCATION
    BS Computer Science, State University, 2020

    SKILLS
    Python, JavaScript, React, AWS
    """
    is_valid, reason = brsr_extractor.assess_brsr_validity(resume_text)
    assert is_valid is False
    assert reason is not None
    assert "doesn't look like a BRSR report" in reason


def test_empty_document_is_rejected():
    is_valid, reason = brsr_extractor.assess_brsr_validity("")
    assert is_valid is False
    assert "no extractable text" in reason


def test_document_with_brsr_title_but_no_principles_is_still_valid():
    # A real filing's cover page alone (before Section C) should pass —
    # the title marker is sufficient on its own.
    text = "This is the Business Responsibility and Sustainability Report for FY 2023-24."
    is_valid, reason = brsr_extractor.assess_brsr_validity(text)
    assert is_valid is True


def test_document_with_enough_principle_sections_but_no_title_is_valid():
    # Three or more substantial "Principle N" sections is independently
    # sufficient, even without the BRSR/NGRBC title phrase.
    filler = "Some substantial disclosure content goes here to pad the section past the minimum length threshold. " * 3
    text = "\n\n".join(f"Principle {n}\n{filler}" for n in range(1, 4))
    is_valid, reason = brsr_extractor.assess_brsr_validity(text)
    assert is_valid is True


def test_short_principle_mentions_dont_count_toward_validity():
    # Table-of-contents-style one-liners shouldn't count as "found" sections.
    text = "\n".join(f"Principle {n} .......... page {n + 3}" for n in range(1, 10))
    is_valid, reason = brsr_extractor.assess_brsr_validity(text)
    assert is_valid is False
