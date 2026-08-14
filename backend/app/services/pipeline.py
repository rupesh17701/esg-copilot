"""End-to-end processing pipeline: raw file bytes -> stored, scored report."""

from sqlalchemy.orm import Session

from app.models.database import Report, ReportChunk
from app.models.schemas import CarbonIntelligenceResult, ESGScoreResult, ExtractedBRSRData
from app.services import brsr_extractor, carbon_intelligence, esg_scoring, pdf_parser
from app.config import get_settings


def process_and_store_report(db: Session, filename: str, file_bytes: bytes) -> Report:
    raw_text = pdf_parser.extract_text(file_bytes, filename)
    normalized = pdf_parser.normalize_whitespace(raw_text)

    structured = brsr_extractor.extract_structured_data(normalized)
    esg_result = esg_scoring.compute_esg_score(structured)
    carbon_result = carbon_intelligence.analyze_carbon(structured)

    settings = get_settings()

    report = Report(
        filename=filename,
        company_name=structured.company_name,
        sector=structured.sector,
        raw_text=normalized,
        extracted_data=structured.model_dump(),
        esg_score=esg_result.model_dump(),
        carbon_metrics=carbon_result.model_dump(),
        extraction_source="anthropic" if settings.llm_configured else "heuristic",
    )
    db.add(report)
    db.flush()

    for i, chunk in enumerate(pdf_parser.chunk_text(normalized)):
        db.add(ReportChunk(report_id=report.id, chunk_index=i, text=chunk))

    db.commit()
    db.refresh(report)
    return report


def parsed_models(report: Report) -> tuple[ExtractedBRSRData, ESGScoreResult, CarbonIntelligenceResult]:
    return (
        ExtractedBRSRData.model_validate(report.extracted_data),
        ESGScoreResult.model_validate(report.esg_score),
        CarbonIntelligenceResult.model_validate(report.carbon_metrics),
    )
