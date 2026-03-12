from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.exam_hall import ExamHall
from app.schemas.exam_hall import ExamHallCreate, ExamHallResponse

router = APIRouter()


@router.post("/", response_model=ExamHallResponse, status_code=status.HTTP_201_CREATED)
def create_hall(payload: ExamHallCreate, db: Session = Depends(get_db)):
    if db.query(ExamHall).filter(ExamHall.name == payload.name).first():
        raise HTTPException(status_code=400, detail="A hall with this name already exists")
    hall = ExamHall(**payload.model_dump())
    db.add(hall)
    db.commit()
    db.refresh(hall)
    return hall


@router.get("/", response_model=List[ExamHallResponse])
def list_halls(db: Session = Depends(get_db)):
    return db.query(ExamHall).order_by(ExamHall.name).all()


@router.get("/{hall_id}", response_model=ExamHallResponse)
def get_hall(hall_id: int, db: Session = Depends(get_db)):
    hall = db.query(ExamHall).filter(ExamHall.id == hall_id).first()
    if not hall:
        raise HTTPException(status_code=404, detail="Exam hall not found")
    return hall


@router.patch("/{hall_id}/deactivate", response_model=ExamHallResponse)
def deactivate_hall(hall_id: int, db: Session = Depends(get_db)):
    hall = db.query(ExamHall).filter(ExamHall.id == hall_id).first()
    if not hall:
        raise HTTPException(status_code=404, detail="Exam hall not found")
    hall.is_active = False
    db.commit()
    db.refresh(hall)
    return hall
