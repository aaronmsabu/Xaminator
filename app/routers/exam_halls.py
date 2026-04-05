from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.exam_hall import ExamHall
from app.models.exam import Exam
from app.models.exam_hall_availability import ExamHallAvailability
from app.models.user import User
from app.schemas.exam_hall import ExamHallCreate, ExamHallResponse
from app.auth import get_current_user
from app.utils.file_parser import parse_upload_file, generate_csv_template

router = APIRouter()


@router.post("/", response_model=ExamHallResponse, status_code=status.HTTP_201_CREATED)
def create_hall(
    payload: ExamHallCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if db.query(ExamHall).filter(ExamHall.name == payload.name).first():
        raise HTTPException(status_code=400, detail="A hall with this name already exists")
    hall = ExamHall(**payload.model_dump())
    db.add(hall)
    db.commit()
    db.refresh(hall)
    return hall


@router.get("/", response_model=List[ExamHallResponse])
def list_halls(
    skip: int = 0,
    limit: int = 10000,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(ExamHall)
    if is_active is not None:
        q = q.filter(ExamHall.is_active == is_active)
    return q.order_by(ExamHall.name).offset(skip).limit(limit).all()


@router.get("/template.csv")
def download_hall_template():
    """Download a CSV template for bulk hall upload."""
    headers = ["name", "block", "floor", "capacity"]
    example_rows = [
        ["Hall A", "Main Block", "1", "60"],
        ["Hall B", "Science Block", "2", "45"],
    ]
    csv_content = generate_csv_template(headers, example_rows)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=halls_template.csv"}
    )


@router.post("/bulk")
async def bulk_upload_halls(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Bulk upload exam halls from CSV or Excel file.
    
    Expected columns: name, block (optional), floor (optional), capacity
    
    If a hall with the same name exists, it will be updated with the new data.
    """
    rows = await parse_upload_file(file)
    
    if not rows:
        raise HTTPException(status_code=400, detail="No data rows found in the file")
    
    # Pre-fetch existing halls
    existing_halls = {h.name.upper(): h for h in db.query(ExamHall).all()}
    
    inserted = 0
    updated = 0
    errors = []
    
    for row_idx, row in enumerate(rows, start=2):
        try:
            # Extract and validate name
            name = row.get("name", "").strip()
            if not name:
                errors.append({"row": row_idx, "field": "name", "message": "Hall name is required"})
                continue
            
            # Extract optional fields
            block = row.get("block", "").strip() or None
            
            floor_str = row.get("floor", "").strip()
            floor = None
            if floor_str:
                try:
                    floor = int(floor_str)
                except ValueError:
                    errors.append({"row": row_idx, "field": "floor", "message": "Floor must be a number"})
                    continue
            
            # Extract and validate capacity
            capacity_str = row.get("capacity", "").strip()
            try:
                capacity = int(capacity_str)
                if capacity <= 0:
                    raise ValueError()
            except ValueError:
                errors.append({"row": row_idx, "field": "capacity", "message": "Capacity must be a positive number"})
                continue
            
            # Check for existing hall
            name_upper = name.upper()
            if name_upper in existing_halls:
                hall = existing_halls[name_upper]
                hall.block = block
                hall.floor = floor
                hall.capacity = capacity
                hall.is_active = True  # Reactivate if previously deactivated
                updated += 1
            else:
                hall = ExamHall(
                    name=name,
                    block=block,
                    floor=floor,
                    capacity=capacity,
                    is_active=True,
                )
                db.add(hall)
                existing_halls[name_upper] = hall
                inserted += 1
                
        except Exception as e:
            errors.append({"row": row_idx, "field": "general", "message": str(e)})
    
    db.commit()
    
    return {
        "inserted": inserted,
        "updated": updated,
        "errors": errors,
        "total_processed": inserted + updated + len(errors),
    }


@router.get("/{hall_id}", response_model=ExamHallResponse)
def get_hall(
    hall_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    hall = db.query(ExamHall).filter(ExamHall.id == hall_id).first()
    if not hall:
        raise HTTPException(status_code=404, detail="Exam hall not found")
    return hall


@router.patch("/{hall_id}/deactivate", response_model=ExamHallResponse)
def deactivate_hall(
    hall_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    hall = db.query(ExamHall).filter(ExamHall.id == hall_id).first()
    if not hall:
        raise HTTPException(status_code=404, detail="Exam hall not found")
    hall.is_active = False
    db.commit()
    db.refresh(hall)
    return hall


@router.patch("/{hall_id}/activate", response_model=ExamHallResponse)
def activate_hall(
    hall_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Reactivate a deactivated hall."""
    hall = db.query(ExamHall).filter(ExamHall.id == hall_id).first()
    if not hall:
        raise HTTPException(status_code=404, detail="Exam hall not found")
    hall.is_active = True
    db.commit()
    db.refresh(hall)
    return hall


# ============ Per-Exam Hall Availability Endpoints ============

@router.get("/exam/{exam_id}/availability")
def get_exam_hall_availability(
    exam_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Get all halls with their availability status for a specific exam.
    
    Returns all active halls with an is_available flag.
    If no explicit availability record exists, the hall is considered available (default).
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Get all active halls
    halls = db.query(ExamHall).filter(ExamHall.is_active == True).order_by(ExamHall.name).all()  # noqa: E712
    
    # Get availability records for this exam
    availabilities = db.query(ExamHallAvailability).filter(
        ExamHallAvailability.exam_id == exam_id
    ).all()
    avail_map = {a.hall_id: a.is_available for a in availabilities}
    
    result = []
    total_capacity = 0
    selected_capacity = 0
    
    for hall in halls:
        # Default to available if no explicit record
        is_available = avail_map.get(hall.id, True)
        result.append({
            "id": hall.id,
            "name": hall.name,
            "block": hall.block,
            "floor": hall.floor,
            "capacity": hall.capacity,
            "is_available": is_available,
        })
        total_capacity += hall.capacity
        if is_available:
            selected_capacity += hall.capacity
    
    return {
        "exam_id": exam_id,
        "halls": result,
        "total_capacity": total_capacity,
        "selected_capacity": selected_capacity,
    }


@router.put("/exam/{exam_id}/availability/{hall_id}")
def set_exam_hall_availability(
    exam_id: int,
    hall_id: int,
    is_available: bool,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Set the availability of a specific hall for a specific exam."""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    hall = db.query(ExamHall).filter(ExamHall.id == hall_id).first()
    if not hall:
        raise HTTPException(status_code=404, detail="Hall not found")
    
    # Find or create availability record
    availability = db.query(ExamHallAvailability).filter(
        ExamHallAvailability.exam_id == exam_id,
        ExamHallAvailability.hall_id == hall_id,
    ).first()
    
    if availability:
        availability.is_available = is_available
    else:
        availability = ExamHallAvailability(
            exam_id=exam_id,
            hall_id=hall_id,
            is_available=is_available,
        )
        db.add(availability)
    
    db.commit()
    
    return {"exam_id": exam_id, "hall_id": hall_id, "is_available": is_available}


@router.post("/exam/{exam_id}/availability/bulk")
def set_exam_halls_availability_bulk(
    exam_id: int,
    hall_ids: List[int],
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Set multiple halls as available for an exam, marking all others as unavailable.
    
    This is a convenience endpoint for the wizard UI where the user selects
    which halls to use for an exam.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    # Get all active halls
    all_halls = db.query(ExamHall).filter(ExamHall.is_active == True).all()  # noqa: E712
    hall_ids_set = set(hall_ids)
    
    # Clear existing availability records for this exam
    db.query(ExamHallAvailability).filter(
        ExamHallAvailability.exam_id == exam_id
    ).delete()
    
    # Create new availability records
    for hall in all_halls:
        availability = ExamHallAvailability(
            exam_id=exam_id,
            hall_id=hall.id,
            is_available=hall.id in hall_ids_set,
        )
        db.add(availability)
    
    db.commit()
    
    selected_capacity = sum(h.capacity for h in all_halls if h.id in hall_ids_set)
    
    return {
        "exam_id": exam_id,
        "selected_halls": len(hall_ids_set),
        "selected_capacity": selected_capacity,
    }
