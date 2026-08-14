"""Heuristic, regex-based structured extraction from raw BRSR report text.

This is the offline extraction path used when no LLM is configured (see
``app.services.llm_client``). It is deliberately conservative: every field is
optional, and failure to find a pattern just leaves the field as ``None``
rather than guessing. When an Anthropic API key is configured, the LLM
extraction path in ``agent.py`` supersedes this for richer, more robust
extraction — this module remains the fallback and the source of the expected
indicator counts used to judge disclosure completeness either way.
"""

import re

from app.models.schemas import (
    NGRBC_PRINCIPLES,
    EnvironmentalMetrics,
    ExtractedBRSRData,
    GovernanceSignals,
    PrincipleDisclosure,
    SocialSignals,
)

# Approximate count of "essential indicators" SEBI's BRSR format expects per
# NGRBC principle. Used only as a denominator for a disclosure-completeness
# proxy score, not as an exact indicator checklist.
EXPECTED_ESSENTIAL_INDICATORS: dict[int, int] = {
    1: 9,
    2: 4,
    3: 14,
    4: 3,
    5: 10,
    6: 15,
    7: 3,
    8: 5,
    9: 5,
}


def _search_float(pattern: str, text: str) -> float | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    raw = match.group(1).replace(",", "")
    try:
        return float(raw)
    except ValueError:
        return None


def _search_int(pattern: str, text: str) -> int | None:
    value = _search_float(pattern, text)
    return int(value) if value is not None else None


def _search_bool(pattern: str, text: str) -> bool | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip().lower().startswith("y")


def _search_str(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip()


NUM = r"([\d,]+(?:\.\d+)?)"


def extract_company_meta(text: str) -> tuple[str, str, str | None]:
    company = _search_str(r"Name of the Listed Entity[:\-\s]+([^\n]+)", text)
    if not company:
        company = _search_str(r"Company Name[:\-\s]+([^\n]+)", text)
    sector = _search_str(r"Sector[:\-\s]+([^\n]+)", text)
    if not sector:
        sector = _search_str(r"Industry[:\-\s]+([^\n]+)", text)
    year = _search_str(r"Financial Year[:\-\s]+([^\n]+)", text)
    if not year:
        year = _search_str(r"Reporting (?:Period|Year)[:\-\s]+([^\n]+)", text)
    return (company or "Unknown Company"), (sector or "Unspecified"), year


def extract_principles(text: str) -> list[PrincipleDisclosure]:
    disclosures: list[PrincipleDisclosure] = []

    # Split the document into per-principle sections using "Principle N" headers.
    splits = re.split(r"(?im)^\s*Principle\s+(\d)\b.*$", text)
    # splits alternates [pre-text, "1", section1, "2", section2, ...].
    # Accumulate as lists and join once — repeated string concatenation in a
    # loop is O(n^2) and can hang on a document with many "Principle N"
    # header matches.
    section_parts_by_principle: dict[int, list[str]] = {}
    for i in range(1, len(splits), 2):
        try:
            num = int(splits[i])
        except ValueError:
            continue
        section_parts_by_principle.setdefault(num, []).append(splits[i + 1])
    section_by_principle: dict[int, str] = {
        num: "".join(parts) for num, parts in section_parts_by_principle.items()
    }

    for num, title in NGRBC_PRINCIPLES.items():
        section = section_by_principle.get(num, "")
        # Proxy for "found" indicators: count Yes/No answers and standalone
        # numeric data points that appear in this principle's section.
        yes_no_hits = len(re.findall(r"\b(Yes|No)\b", section))
        numeric_hits = len(re.findall(r"\b\d+(?:\.\d+)?%?\b", section))
        found = min(EXPECTED_ESSENTIAL_INDICATORS[num], max(yes_no_hits, numeric_hits // 3))
        leadership_hits = len(re.findall(r"(?i)leadership indicator", section))

        notes = []
        if not section.strip():
            notes.append("No dedicated section detected for this principle in the report text.")

        disclosures.append(
            PrincipleDisclosure(
                principle=num,
                title=title,
                essential_indicators_found=found,
                essential_indicators_expected=EXPECTED_ESSENTIAL_INDICATORS[num],
                leadership_indicators_found=leadership_hits,
                notes=notes,
            )
        )
    return disclosures


def extract_environmental(text: str) -> EnvironmentalMetrics:
    return EnvironmentalMetrics(
        scope1_emissions_tco2e=_search_float(
            rf"Total Scope\s*1[^\n]*?{NUM}\s*(?:Metric\s*)?(?:tonnes|tCO2e|MT)", text
        ),
        scope2_emissions_tco2e=_search_float(
            rf"Total Scope\s*2[^\n]*?{NUM}\s*(?:Metric\s*)?(?:tonnes|tCO2e|MT)", text
        ),
        scope3_emissions_tco2e=_search_float(
            rf"Total Scope\s*3[^\n]*?{NUM}\s*(?:Metric\s*)?(?:tonnes|tCO2e|MT)", text
        ),
        total_energy_consumption_gj=_search_float(
            rf"Total energy consumption[^\n]*?{NUM}\s*(?:GJ|gigajoules)", text
        ),
        renewable_energy_pct=_search_float(
            rf"Renewable energy[^\n]*?{NUM}\s*%", text
        ),
        water_withdrawal_kl=_search_float(
            rf"(?:Total )?[Ww]ater withdrawal[^\n]*?{NUM}\s*(?:KL|kilolitres)", text
        ),
        water_recycled_pct=_search_float(
            rf"[Ww]ater recycled[^\n]*?{NUM}\s*%", text
        ),
        total_waste_generated_mt=_search_float(
            rf"Total waste generated[^\n]*?{NUM}\s*(?:Metric\s*tonnes|MT)", text
        ),
        waste_recycled_pct=_search_float(
            rf"[Ww]aste recycled[^\n]*?{NUM}\s*%", text
        ),
        revenue_inr_crore=_search_float(
            rf"(?:Total )?[Rr]evenue(?: from operations)?[^\n]*?(?:INR|Rs\.?)?\s*{NUM}\s*(?:crore|Cr)", text
        ),
    )


def extract_governance(text: str) -> GovernanceSignals:
    return GovernanceSignals(
        board_independence_pct=_search_float(
            rf"[Bb]oard [Ii]ndependence[^\n]*?{NUM}\s*%", text
        ),
        anti_corruption_policy=_search_bool(
            r"[Aa]nti-?corruption policy[^\n]*?\b(Yes|No)\b", text
        ),
        whistleblower_mechanism=_search_bool(
            r"[Ww]histle ?blower mechanism[^\n]*?\b(Yes|No)\b", text
        ),
        complaints_received=_search_int(
            rf"[Cc]omplaints received[^\n]*?{NUM}", text
        ),
        complaints_resolved=_search_int(
            rf"[Cc]omplaints resolved[^\n]*?{NUM}", text
        ),
    )


def extract_social(text: str) -> SocialSignals:
    return SocialSignals(
        employee_wellbeing_coverage_pct=_search_float(
            rf"[Ee]mployee wellbeing[^\n]*?{NUM}\s*%", text
        ),
        safety_incidents_total=_search_int(
            rf"[Tt]otal (?:recordable )?safety incidents[^\n]*?{NUM}", text
        ),
        human_rights_complaints=_search_int(
            rf"[Hh]uman [Rr]ights complaints[^\n]*?{NUM}", text
        ),
        csr_spend_inr_crore=_search_float(
            rf"CSR spend[^\n]*?{NUM}\s*(?:crore|Cr)", text
        ),
        women_workforce_pct=_search_float(
            rf"[Ww]omen (?:in workforce|employees)[^\n]*?{NUM}\s*%", text
        ),
    )


def extract_structured_data(text: str) -> ExtractedBRSRData:
    company, sector, year = extract_company_meta(text)
    return ExtractedBRSRData(
        company_name=company,
        sector=sector,
        reporting_year=year,
        principles=extract_principles(text),
        environment=extract_environmental(text),
        governance=extract_governance(text),
        social=extract_social(text),
    )
