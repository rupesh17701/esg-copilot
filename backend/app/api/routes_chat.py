from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.database import ChatMessage, Report, ReportChunk, get_db
from app.models.schemas import ChatMessageOut, ChatRequest, ChatResponse
from app.services.agent import answer_question
from app.services.llm_client import ChatTurn
from app.services.pipeline import parsed_models

router = APIRouter(prefix="/api/reports/{report_id}/chat", tags=["chat"])

MAX_HISTORY_TURNS = 6


@router.get("", response_model=list[ChatMessageOut])
def get_chat_history(report_id: int, db: Session = Depends(get_db)) -> list[ChatMessageOut]:
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return [
        ChatMessageOut(role=m.role, content=m.content, created_at=m.created_at.isoformat())
        for m in report.messages
    ]


@router.post("", response_model=ChatResponse)
def send_chat_message(report_id: int, payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    data, esg, carbon = parsed_models(report)
    chunks = [c.text for c in db.query(ReportChunk).filter(ReportChunk.report_id == report_id).order_by(ReportChunk.chunk_index)]

    history_rows = report.messages[-(MAX_HISTORY_TURNS * 2) :]
    history = [ChatTurn(role=m.role, content=m.content) for m in history_rows]

    response = answer_question(chunks, data, esg, carbon, history, payload.message)

    db.add(ChatMessage(report_id=report_id, role="user", content=payload.message))
    db.add(ChatMessage(report_id=report_id, role="assistant", content=response.reply))
    db.commit()

    return response
