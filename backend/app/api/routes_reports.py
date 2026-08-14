from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.models.database import Report, get_db
from app.models.schemas import ReportDetail, ReportSummary
from app.services.agent import generate_summary
from app.services.pipeline import NotABRSRReportError, parsed_models, process_and_store_report

router = APIRouter(prefix="/api/reports", tags=["reports"])

ALLOWED_EXTENSIONS = (".pdf", ".txt")


@router.post("", response_model=ReportDetail, status_code=201)
async def upload_report(file: UploadFile, db: Session = Depends(get_db)) -> ReportDetail:
    if not file.filename or not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=400, detail="Only .pdf and .txt files are supported")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        report = process_and_store_report(db, file.filename, file_bytes)
    except NotABRSRReportError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_detail(report)


@router.get("", response_model=list[ReportSummary])
def list_reports(db: Session = Depends(get_db)) -> list[ReportSummary]:
    reports = db.query(Report).order_by(Report.created_at.desc()).all()
    return [_to_summary(r) for r in reports]


@router.get("/{report_id}", response_model=ReportDetail)
def get_report(report_id: int, db: Session = Depends(get_db)) -> ReportDetail:
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return _to_detail(report)


@router.get("/{report_id}/summary")
def get_narrative_summary(report_id: int, db: Session = Depends(get_db)) -> dict:
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    data, esg, carbon = parsed_models(report)
    summary, source = generate_summary(data, esg, carbon)
    return {"summary": summary, "source": source}


@router.delete("/{report_id}", status_code=204)
def delete_report(report_id: int, db: Session = Depends(get_db)) -> None:
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    db.delete(report)
    db.commit()


def _to_summary(report: Report) -> ReportSummary:
    return ReportSummary(
        id=report.id,
        filename=report.filename,
        company_name=report.company_name,
        sector=report.sector,
        created_at=report.created_at.isoformat(),
        extraction_source=report.extraction_source,
    )


def _to_detail(report: Report) -> ReportDetail:
    data, esg, carbon = parsed_models(report)
    return ReportDetail(
        **_to_summary(report).model_dump(),
        extracted_data=data,
        esg_score=esg,
        carbon_metrics=carbon,
    )
