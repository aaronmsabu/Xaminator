from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.exam import Exam
from app.models.department import Department
from app.schemas.exam import ExamCreate, ExamStatusUpdate, ExamResponse

router = APIRouter()


@router.post("/", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def create_exam(payload: ExamCreate, db: Session = Depends(get_db)):
    if payload.department_id and not db.query(Department).filter(
        Department.id == payload.department_id
    ).first():
        raise HTTPException(status_code=404, detail="Department not found")
    exam = Exam(**payload.model_dump())
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


@router.get("/", response_model=List[ExamResponse])
def list_exams(
    status: Optional[str] = None,
    department_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Exam)
    if status:
        q = q.filter(Exam.status == status)
    if department_id is not None:
        q = q.filter(Exam.department_id == department_id)
    return q.order_by(Exam.exam_date).all()


@router.get("/{exam_id}", response_model=ExamResponse)
def get_exam(exam_id: int, db: Session = Depends(get_db)):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    return exam


@router.patch("/{exam_id}/status", response_model=ExamResponse)
def update_exam_status(exam_id: int, payload: ExamStatusUpdate, db: Session = Depends(get_db)):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    exam.status = payload.status
    db.commit()
    db.refresh(exam)
    return exam
