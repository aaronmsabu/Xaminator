from datetime import datetime as dt
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.exam import Exam
from app.models.department import Department
from app.models.user import User
from app.schemas.exam import ExamCreate, ExamStatusUpdate, ExamResponse
from app.auth import get_current_user
from app.utils.file_parser import parse_upload_file, generate_csv_template

router = APIRouter()


@router.post("/", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def create_exam(
    payload: ExamCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
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
    semester: Optional[int] = None,
    skip: int = 0,
    limit: int = 10000,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Exam)
    if status:
        q = q.filter(Exam.status == status)
    if department_id is not None:
        q = q.filter(Exam.department_id == department_id)
    if semester is not None:
        q = q.filter(Exam.semester == semester)
    return q.order_by(Exam.exam_date.desc()).offset(skip).limit(limit).all()


@router.get("/template.csv")
def download_exam_template():
    """Download a CSV template for bulk exam upload."""
    headers = ["title", "exam_date", "start_time", "end_time", "academic_year", "semester", "department_code"]
    example_rows = [
        ["Mathematics Final", "2026-04-15", "09:00", "12:00", "2025-26", "4", "CS"],
        ["Physics Midterm", "2026-04-16", "14:00", "16:00", "2025-26", "2", ""],  # Empty dept = all departments
    ]
    csv_content = generate_csv_template(headers, example_rows)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=exams_template.csv"}
    )


@router.post("/bulk")
async def bulk_upload_exams(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Bulk upload exams from CSV or Excel file.
    
    Expected columns: title, exam_date (YYYY-MM-DD), start_time (HH:MM), end_time (HH:MM),
                      academic_year, semester, department_code (optional)
    
    If an exam with the same title, date, semester, and department exists, it will be skipped.
    """
    rows = await parse_upload_file(file)
    
    if not rows:
        raise HTTPException(status_code=400, detail="No data rows found in the file")
    
    # Pre-fetch departments
    departments = db.query(Department).all()
    dept_by_code = {d.code.upper(): d for d in departments}
    dept_by_name = {d.name.upper(): d for d in departments}
    
    inserted = 0
    skipped = 0
    errors = []
    
    for row_idx, row in enumerate(rows, start=2):
        try:
            # Extract and validate title
            title = row.get("title", "").strip()
            if not title:
                errors.append({"row": row_idx, "field": "title", "message": "Title is required"})
                continue
            
            # Extract and validate exam_date
            date_str = row.get("exam_date", "").strip()
            try:
                exam_date = dt.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                errors.append({"row": row_idx, "field": "exam_date", "message": "Date must be in YYYY-MM-DD format"})
                continue
            
            # Extract and validate start_time
            start_str = row.get("start_time", "").strip()
            try:
                # Handle both HH:MM and HH:MM:SS formats
                if len(start_str) == 5:
                    start_time = dt.strptime(start_str, "%H:%M").time()
                else:
                    start_time = dt.strptime(start_str, "%H:%M:%S").time()
            except ValueError:
                errors.append({"row": row_idx, "field": "start_time", "message": "Start time must be in HH:MM format"})
                continue
            
            # Extract and validate end_time
            end_str = row.get("end_time", "").strip()
            try:
                if len(end_str) == 5:
                    end_time = dt.strptime(end_str, "%H:%M").time()
                else:
                    end_time = dt.strptime(end_str, "%H:%M:%S").time()
            except ValueError:
                errors.append({"row": row_idx, "field": "end_time", "message": "End time must be in HH:MM format"})
                continue
            
            if end_time <= start_time:
                errors.append({"row": row_idx, "field": "end_time", "message": "End time must be after start time"})
                continue
            
            # Extract academic_year
            academic_year = row.get("academic_year", "").strip()
            if not academic_year:
                errors.append({"row": row_idx, "field": "academic_year", "message": "Academic year is required"})
                continue
            
            # Extract and validate semester
            semester_str = row.get("semester", "").strip()
            try:
                semester = int(semester_str)
                if not 1 <= semester <= 12:
                    raise ValueError()
            except ValueError:
                errors.append({"row": row_idx, "field": "semester", "message": "Semester must be a number between 1 and 12"})
                continue
            
            # Extract department (optional)
            dept_code = row.get("department_code", "").strip().upper()
            dept_name = row.get("department", "").strip().upper()
            department_id = None
            
            if dept_code and dept_code in dept_by_code:
                department_id = dept_by_code[dept_code].id
            elif dept_name and dept_name in dept_by_name:
                department_id = dept_by_name[dept_name].id
            elif dept_code or dept_name:
                # Non-empty but not found
                errors.append({"row": row_idx, "field": "department_code", "message": f"Department not found: {dept_code or dept_name}"})
                continue
            
            # Check for duplicate exam
            existing = db.query(Exam).filter(
                Exam.title == title,
                Exam.exam_date == exam_date,
                Exam.semester == semester,
                Exam.department_id == department_id,
            ).first()
            
            if existing:
                skipped += 1
                continue
            
            # Create exam
            exam = Exam(
                title=title,
                exam_date=exam_date,
                start_time=start_time,
                end_time=end_time,
                academic_year=academic_year,
                semester=semester,
                department_id=department_id,
                status="scheduled",
            )
            db.add(exam)
            inserted += 1
            
        except Exception as e:
            errors.append({"row": row_idx, "field": "general", "message": str(e)})
    
    db.commit()
    
    return {
        "inserted": inserted,
        "skipped": skipped,
        "errors": errors,
        "total_processed": inserted + skipped + len(errors),
    }


@router.get("/{exam_id}", response_model=ExamResponse)
def get_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    return exam


@router.patch("/{exam_id}/status", response_model=ExamResponse)
def update_exam_status(
    exam_id: int,
    payload: ExamStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    exam.status = payload.status
    db.commit()
    db.refresh(exam)
    return exam
