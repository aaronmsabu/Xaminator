from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.exam_session import ExamSession
from app.models.user import User
from app.schemas.exam_session import ExamSessionCreate, ExamSessionResponse
from app.auth import get_current_user

router = APIRouter()


@router.post("/", response_model=ExamSessionResponse, status_code=status.HTTP_201_CREATED)
def create_exam_session(
    payload: ExamSessionCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Create a new exam session (physical time-slot shared by multiple exams)."""
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")

    session_obj = ExamSession(**payload.model_dump())
    db.add(session_obj)
    db.commit()
    db.refresh(session_obj)
    return session_obj


@router.get("/", response_model=List[ExamSessionResponse])
def list_exam_sessions(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """List exam sessions, optionally filtered by status."""
    q = db.query(ExamSession)
    if status:
        q = q.filter(ExamSession.status == status)
    return q.order_by(ExamSession.exam_date.desc()).offset(skip).limit(limit).all()


@router.get("/{session_id}", response_model=ExamSessionResponse)
def get_exam_session(
    session_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    session_obj = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Exam session not found")
    return session_obj
