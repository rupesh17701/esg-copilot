"""The ESG Copilot agent: retrieval + structured metrics + LLM (or offline
fallback) composed into question-answering and narrative summary generation.
"""

from app.models.schemas import (
    CarbonIntelligenceResult,
    ChatResponse,
    ESGScoreResult,
    ExtractedBRSRData,
)
from app.services.llm_client import ChatTurn, get_llm_client
from app.services.rag import retrieve_relevant_chunks


def _metrics_context(data: ExtractedBRSRData, esg: ESGScoreResult, carbon: CarbonIntelligenceResult) -> str:
    lines = [
        f"Company: {data.company_name} | Sector: {data.sector} | Reporting year: {data.reporting_year or 'unknown'}",
        f"Overall ESG score: {esg.overall_score}/100 (risk band: {esg.risk_band})",
        f"Disclosure completeness across all 9 NGRBC principles: {esg.disclosure_completeness_pct}%",
    ]
    for dim in esg.dimensions:
        lines.append(f"{dim.dimension.title()} score: {dim.score}/100")
    lines.append(
        f"Scope 1+2 emissions: {carbon.total_scope12_tco2e or 'not disclosed'} tCO2e "
        f"(Scope 1: {carbon.scope1_tco2e or 'n/a'}, Scope 2: {carbon.scope2_tco2e or 'n/a'}, "
        f"Scope 3: {carbon.scope3_tco2e or 'not disclosed'})"
    )
    if carbon.carbon_intensity_per_revenue is not None:
        lines.append(
            f"Carbon intensity: {carbon.carbon_intensity_per_revenue} tCO2e per INR crore revenue "
            f"({carbon.benchmark_position} vs. sector benchmark)"
        )
    if carbon.renewable_energy_pct is not None:
        lines.append(f"Renewable energy share: {carbon.renewable_energy_pct}%")
    return "\n".join(lines)


def generate_summary(
    data: ExtractedBRSRData, esg: ESGScoreResult, carbon: CarbonIntelligenceResult
) -> tuple[str, str]:
    client = get_llm_client()
    context = _metrics_context(data, esg, carbon)
    summary = client.generate_summary(context)
    return summary, client.source


def answer_question(
    chunks: list[str],
    data: ExtractedBRSRData,
    esg: ESGScoreResult,
    carbon: CarbonIntelligenceResult,
    history: list[ChatTurn],
    question: str,
) -> ChatResponse:
    client = get_llm_client()
    retrieved = retrieve_relevant_chunks(chunks, question, top_k=4)

    context_parts = [_metrics_context(data, esg, carbon), "\nRelevant report excerpts:"]
    citations: list[str] = []
    for idx, chunk, score in retrieved:
        if score <= 0 and len(retrieved) > 1:
            continue
        context_parts.append(f"[Excerpt {idx}]\n{chunk}")
        citations.append(f"Excerpt {idx}")
    context = "\n\n".join(context_parts)

    reply = client.chat(context, history, question)
    return ChatResponse(reply=reply, source=client.source, citations=citations)
