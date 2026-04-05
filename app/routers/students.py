import re
from enum import Enum
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional

from app.database import get_db
from app.models.student import Student
from app.models.department import Department
from app.models.user import User
from app.schemas.student import StudentCreate, StudentUpdate, StudentResponse
from app.auth import get_current_user
from app.utils.file_parser import parse_upload_file, generate_csv_template

router = APIRouter()


class OnDuplicateAction(str, Enum):
    skip = "skip"
    update = "update"


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
    limit: int = 10000,
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


@router.get("/count")
def count_students(
    department_id: Optional[int] = None,
    semester: Optional[int] = None,
    is_active: Optional[bool] = True,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get count of students matching filters."""
    q = db.query(Student)
    if department_id is not None:
        q = q.filter(Student.department_id == department_id)
    if semester is not None:
        q = q.filter(Student.semester == semester)
    if is_active is not None:
        q = q.filter(Student.is_active == is_active)
    return {"count": q.count()}


@router.get("/template.csv")
def download_student_template():
    """Download a CSV template for bulk student upload."""
    headers = ["register_number", "full_name", "email", "department_code", "semester"]
    example_rows = [
        ["REG001", "John Doe", "john@example.com", "CS", "3"],
        ["REG002", "Jane Smith", "jane@example.com", "EC", "5"],
    ]
    csv_content = generate_csv_template(headers, example_rows)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=students_template.csv"}
    )


@router.post("/bulk")
async def bulk_upload_students(
    file: UploadFile = File(...),
    on_duplicate: OnDuplicateAction = Query(OnDuplicateAction.skip),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Bulk upload students from CSV or Excel file.
    
    Expected columns: register_number, full_name, email (optional), department_code, semester
    
    on_duplicate options:
    - skip: Skip rows where register_number already exists
    - update: Update existing student records with new data
    """
    rows = await parse_upload_file(file)
    
    if not rows:
        raise HTTPException(status_code=400, detail="No data rows found in the file")
    
    # Pre-fetch all departments for lookup
    departments = db.query(Department).all()
    dept_by_code = {d.code.upper(): d for d in departments}
    dept_by_name = {d.name.upper(): d for d in departments}
    
    # Pre-fetch existing students for duplicate check
    existing_students = {s.register_number: s for s in db.query(Student).all()}
    
    inserted = 0
    updated = 0
    skipped = 0
    errors = []
    
    for row_idx, row in enumerate(rows, start=2):  # Start at 2 (header is row 1)
        try:
            # Extract and validate register_number
            reg_num = row.get("register_number", "").strip().upper()
            if not reg_num:
                errors.append({"row": row_idx, "field": "register_number", "message": "Register number is required"})
                continue
            if not re.match(r"^[A-Z0-9]{5,20}$", reg_num):
                errors.append({"row": row_idx, "field": "register_number", "message": "Register number must be 5-20 alphanumeric characters"})
                continue
            
            # Extract and validate full_name
            full_name = row.get("full_name", "").strip()
            if not full_name:
                errors.append({"row": row_idx, "field": "full_name", "message": "Full name is required"})
                continue
            
            # Extract email (optional)
            email = row.get("email", "").strip() or None
            
            # Extract and validate department
            dept_code = row.get("department_code", "").strip().upper()
            dept_name = row.get("department", "").strip().upper()
            dept_id_str = row.get("department_id", "").strip()
            
            department = None
            if dept_code and dept_code in dept_by_code:
                department = dept_by_code[dept_code]
            elif dept_name and dept_name in dept_by_name:
                department = dept_by_name[dept_name]
            elif dept_id_str:
                try:
                    dept_id = int(dept_id_str)
                    department = next((d for d in departments if d.id == dept_id), None)
                except ValueError:
                    pass
            
            if not department:
                errors.append({"row": row_idx, "field": "department_code", "message": f"Department not found: {dept_code or dept_name or dept_id_str}"})
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
            
            # Check for duplicate
            if reg_num in existing_students:
                if on_duplicate == OnDuplicateAction.skip:
                    skipped += 1
                    continue
                else:  # update
                    student = existing_students[reg_num]
                    student.full_name = full_name
                    student.email = email
                    student.department_id = department.id
                    student.semester = semester
                    updated += 1
            else:
                # Create new student
                student = Student(
                    register_number=reg_num,
                    full_name=full_name,
                    email=email,
                    department_id=department.id,
                    semester=semester,
                    is_active=True,
                )
                db.add(student)
                existing_students[reg_num] = student  # Track for subsequent duplicate checks
                inserted += 1
                
        except Exception as e:
            errors.append({"row": row_idx, "field": "general", "message": str(e)})
    
    db.commit()
    
    return {
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
        "total_processed": inserted + updated + skipped + len(errors),
    }


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
