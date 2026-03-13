from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional

from app.database import get_db
from app.models.student import Student
from app.models.department import Department
from app.models.user import User
from app.schemas.student import StudentCreate, StudentUpdate, StudentResponse
from app.auth import get_current_user

router = APIRouter()


@router.post("/", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: StudentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if not db.query(Department).filter(Department.id == payload.department_id).first():
        raise HTTPException(status_code=404, detail="Department not found")
    if db.query(Student).filter(Student.register_number == payload.register_number).first():
        raise HTTPException(status_code=400, detail="Register number already exists")
    student = Student(**payload.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.get("/", response_model=List[StudentResponse])
def list_students(
    department_id: Optional[int] = None,
    semester: Optional[int] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Student)
    if department_id is not None:
        q = q.filter(Student.department_id == department_id)
    if semester is not None:
        q = q.filter(Student.semester == semester)
    if is_active is not None:
        q = q.filter(Student.is_active == is_active)
    # Server-side search by name or register number
    if search:
        search_term = f"%{search}%"
        q = q.filter(
            or_(
                Student.full_name.ilike(search_term),
                Student.register_number.ilike(search_term),
            )
        )
    return q.order_by(Student.register_number).offset(skip).limit(limit).all()


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.patch("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: int,
    payload: StudentUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(student, field, value)
    db.commit()
    db.refresh(student)
    return student


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    db.delete(student)
    db.commit()
