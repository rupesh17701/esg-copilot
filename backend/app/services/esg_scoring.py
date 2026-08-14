"""Rule-based ESG risk scoring engine.

Produces a 0-100 score per dimension (Environmental, Social, Governance)
from the structured BRSR data, plus an overall score and qualitative risk
band. This is deliberately transparent and rule-based (not an LLM call) so
scores are reproducible and auditable — every point is traceable to a
specific disclosed figure via the ``rationale`` list.
"""

from app.models.schemas import DimensionScore, ESGScoreResult, ExtractedBRSRData

SOCIAL_PRINCIPLES = {3, 4, 5, 8, 9}
GOVERNANCE_PRINCIPLES = {1, 7}
ENVIRONMENT_PRINCIPLES = {6}


def _avg_completeness(data: ExtractedBRSRData, principle_nums: set[int]) -> float:
    matches = [p for p in data.principles if p.principle in principle_nums]
    if not matches:
        return 0.0
    return sum(p.disclosure_completeness for p in matches) / len(matches)


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def score_environmental(data: ExtractedBRSRData) -> DimensionScore:
    rationale: list[str] = []
    env = data.environment
    score = 0.0

    disclosure = _avg_completeness(data, ENVIRONMENT_PRINCIPLES)
    contribution = _clamp(disclosure) * 0.40
    score += contribution
    rationale.append(f"Principle 6 (Environment) disclosure completeness: {disclosure:.0f}% -> {contribution:.1f}/40 pts")

    if env.renewable_energy_pct is not None:
        contribution = _clamp(env.renewable_energy_pct) * 0.20
        score += contribution
        rationale.append(f"Renewable energy share: {env.renewable_energy_pct:.0f}% -> {contribution:.1f}/20 pts")
    else:
        score += 8.0
        rationale.append("Renewable energy share not disclosed -> neutral 8/20 pts")

    intensity = env.carbon_intensity_per_revenue
    if intensity is not None:
        # Lower intensity is better. 1.0 tCO2e/INR-crore treated as a strong
        # baseline (in line with the sector benchmark table's lower bounds);
        # anything at or below scores full marks, scaling down to 0 at 10.0
        # and above (in line with carbon-intensive sectors like steel/power).
        if intensity <= 1.0:
            contribution = 20.0
        elif intensity >= 10.0:
            contribution = 0.0
        else:
            contribution = 20.0 * (1 - (intensity - 1.0) / 9.0)
        score += contribution
        rationale.append(f"Carbon intensity: {intensity:.3f} tCO2e/INR-crore -> {contribution:.1f}/20 pts")
    else:
        score += 8.0
        rationale.append("Carbon intensity not computable (missing emissions or revenue) -> neutral 8/20 pts")

    recycle_signals = [v for v in (env.water_recycled_pct, env.waste_recycled_pct) if v is not None]
    if recycle_signals:
        avg_recycle = sum(recycle_signals) / len(recycle_signals)
        contribution = _clamp(avg_recycle) * 0.20
        score += contribution
        rationale.append(f"Water/waste recycling average: {avg_recycle:.0f}% -> {contribution:.1f}/20 pts")
    else:
        score += 8.0
        rationale.append("Recycling data not disclosed -> neutral 8/20 pts")

    return DimensionScore(dimension="environmental", score=round(_clamp(score), 1), rationale=rationale)


def score_social(data: ExtractedBRSRData) -> DimensionScore:
    rationale: list[str] = []
    social = data.social
    score = 0.0

    disclosure = _avg_completeness(data, SOCIAL_PRINCIPLES)
    contribution = _clamp(disclosure) * 0.40
    score += contribution
    rationale.append(f"Social principles (3,4,5,8,9) disclosure completeness: {disclosure:.0f}% -> {contribution:.1f}/40 pts")

    if social.safety_incidents_total is not None:
        # 0 incidents -> full marks; 20+ incidents -> 0.
        contribution = _clamp(20.0 * (1 - social.safety_incidents_total / 20.0))
        score += contribution
        rationale.append(f"Safety incidents reported: {social.safety_incidents_total} -> {contribution:.1f}/20 pts")
    else:
        score += 8.0
        rationale.append("Safety incident data not disclosed -> neutral 8/20 pts")

    if social.csr_spend_inr_crore is not None and social.csr_spend_inr_crore > 0:
        score += 15.0
        rationale.append(f"CSR spend disclosed (INR {social.csr_spend_inr_crore:.2f} crore) -> 15/15 pts")
    else:
        rationale.append("CSR spend not disclosed or zero -> 0/15 pts")

    if social.women_workforce_pct is not None:
        contribution = _clamp(social.women_workforce_pct / 40.0 * 15.0, high=15.0)
        score += contribution
        rationale.append(f"Women in workforce: {social.women_workforce_pct:.0f}% -> {contribution:.1f}/15 pts")
    else:
        score += 6.0
        rationale.append("Workforce diversity not disclosed -> neutral 6/15 pts")

    if social.human_rights_complaints is not None:
        contribution = _clamp(10.0 * (1 - social.human_rights_complaints / 10.0))
        score += contribution
        rationale.append(f"Human rights complaints: {social.human_rights_complaints} -> {contribution:.1f}/10 pts")
    else:
        score += 4.0
        rationale.append("Human rights complaint data not disclosed -> neutral 4/10 pts")

    return DimensionScore(dimension="social", score=round(_clamp(score), 1), rationale=rationale)


def score_governance(data: ExtractedBRSRData) -> DimensionScore:
    rationale: list[str] = []
    gov = data.governance
    score = 0.0

    disclosure = _avg_completeness(data, GOVERNANCE_PRINCIPLES)
    contribution = _clamp(disclosure) * 0.40
    score += contribution
    rationale.append(f"Governance principles (1,7) disclosure completeness: {disclosure:.0f}% -> {contribution:.1f}/40 pts")

    if gov.board_independence_pct is not None:
        contribution = _clamp(gov.board_independence_pct) * 0.25
        score += contribution
        rationale.append(f"Board independence: {gov.board_independence_pct:.0f}% -> {contribution:.1f}/25 pts")
    else:
        score += 10.0
        rationale.append("Board independence not disclosed -> neutral 10/25 pts")

    if gov.anti_corruption_policy:
        score += 15.0
        rationale.append("Anti-corruption policy in place -> 15/15 pts")
    elif gov.anti_corruption_policy is False:
        rationale.append("No anti-corruption policy disclosed -> 0/15 pts")
    else:
        score += 6.0
        rationale.append("Anti-corruption policy status not disclosed -> neutral 6/15 pts")

    if gov.whistleblower_mechanism:
        score += 10.0
        rationale.append("Whistleblower mechanism in place -> 10/10 pts")
    elif gov.whistleblower_mechanism is False:
        rationale.append("No whistleblower mechanism disclosed -> 0/10 pts")
    else:
        score += 4.0
        rationale.append("Whistleblower mechanism status not disclosed -> neutral 4/10 pts")

    if gov.complaints_received is not None and gov.complaints_received > 0:
        resolved = gov.complaints_resolved or 0
        resolution_rate = min(1.0, resolved / gov.complaints_received)
        contribution = 10.0 * resolution_rate
        score += contribution
        rationale.append(
            f"Complaint resolution rate: {resolved}/{gov.complaints_received} -> {contribution:.1f}/10 pts"
        )
    else:
        score += 5.0
        rationale.append("Complaints data not disclosed or none received -> neutral 5/10 pts")

    return DimensionScore(dimension="governance", score=round(_clamp(score), 1), rationale=rationale)


def compute_esg_score(data: ExtractedBRSRData) -> ESGScoreResult:
    dimensions = [score_environmental(data), score_social(data), score_governance(data)]
    overall = round(sum(d.score for d in dimensions) / len(dimensions), 1)

    if overall >= 75:
        band = "Low"
    elif overall >= 60:
        band = "Moderate"
    elif overall >= 40:
        band = "Elevated"
    else:
        band = "High"

    completeness = (
        round(sum(p.disclosure_completeness for p in data.principles) / len(data.principles), 1)
        if data.principles
        else 0.0
    )

    return ESGScoreResult(
        overall_score=overall,
        risk_band=band,
        dimensions=dimensions,
        disclosure_completeness_pct=completeness,
    )
