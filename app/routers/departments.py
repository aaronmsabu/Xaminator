from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.department import Department
from app.models.user import User
from app.schemas.department import DepartmentCreate, DepartmentResponse
from app.auth import get_current_user

router = APIRouter()


@router.post("/", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if db.query(Department).filter(
        (Department.name == payload.name) | (Department.code == payload.code)
    ).first():
        raise HTTPException(
            status_code=400,
            detail="A department with this name or code already exists",
        )
    dept = Department(**payload.model_dump())
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


@router.get("/", response_model=List[DepartmentResponse])
def list_departments(
    skip: Optional[int] = 0,
    limit: Optional[int] = 100,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return db.query(Department).order_by(Department.name).offset(skip).limit(limit).all()


@router.get("/{department_id}", response_model=DepartmentResponse)
def get_department(
    department_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    dept = db.query(Department).filter(Department.id == department_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept
