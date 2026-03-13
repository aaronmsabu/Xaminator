from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.seat_allocation import SeatAllocation
from app.models.exam import Exam
from app.models.student import Student
from app.models.user import User
from app.schemas.seat_allocation import (
    GenerateSeatingRequest,
    SeatingResponse,
    SeatAllocationDetail,
)
from app.services.seat_allocation import generate_seating
from app.auth import get_current_user

router = APIRouter()


@router.post("/generate-seating", status_code=status.HTTP_201_CREATED)
def generate_seating_route(
    payload: GenerateSeatingRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        allocations = generate_seating(payload.exam_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "message": f"Seating generated successfully. {len(allocations)} students allocated."
    }


@router.get("/seating/{exam_id}", response_model=SeatingResponse)
def get_seating(
    exam_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if not db.query(Exam).filter(Exam.id == exam_id).first():
        raise HTTPException(status_code=404, detail="Exam not found")

    rows = (
        db.query(SeatAllocation)
        .options(
            joinedload(SeatAllocation.student).joinedload(Student.department),
            joinedload(SeatAllocation.hall),
        )
        .filter(SeatAllocation.exam_id == exam_id)
        .order_by(SeatAllocation.hall_id, SeatAllocation.seat_number)
        .all()
    )

    details = [
        SeatAllocationDetail(
            id=row.id,
            seat_number=row.seat_number,
            hall_name=row.hall.name,
            student_name=row.student.full_name,
            register_number=row.student.register_number,
            department_name=row.student.department.name,
        )
        for row in rows
    ]

    return SeatingResponse(
        exam_id=exam_id,
        total_allocated=len(details),
        allocations=details,
    )
