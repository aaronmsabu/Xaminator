import io
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
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


@router.get("/seating/{exam_id}/export/excel")
def export_seating_excel(
    exam_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Export seating arrangement to Excel file.
    
    Creates one sheet per hall with all students assigned to that hall.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
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

    if not rows:
        raise HTTPException(status_code=404, detail="No seating allocations found for this exam")

    # Group by hall
    halls_data = {}
    for row in rows:
        hall_name = row.hall.name
        if hall_name not in halls_data:
            halls_data[hall_name] = {
                "block": row.hall.block,
                "floor": row.hall.floor,
                "students": []
            }
        halls_data[hall_name]["students"].append({
            "seat_number": row.seat_number,
            "register_number": row.student.register_number,
            "full_name": row.student.full_name,
            "department": row.student.department.name,
        })

    # Create workbook
    wb = Workbook()
    wb.remove(wb.active)  # Remove default sheet

    # Styles
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    for hall_name, data in halls_data.items():
        # Create sheet for each hall (truncate name if too long for Excel)
        sheet_name = hall_name[:31] if len(hall_name) > 31 else hall_name
        ws = wb.create_sheet(title=sheet_name)

        # Title row
        ws.merge_cells('A1:D1')
        ws['A1'] = f"Seating Arrangement - {hall_name}"
        ws['A1'].font = Font(bold=True, size=14)
        ws['A1'].alignment = Alignment(horizontal="center")

        # Exam info
        ws.merge_cells('A2:D2')
        ws['A2'] = f"Exam: {exam.title} | Date: {exam.exam_date} | Time: {exam.start_time} - {exam.end_time}"
        ws['A2'].alignment = Alignment(horizontal="center")

        # Hall info
        hall_info = f"Hall: {hall_name}"
        if data['block']:
            hall_info += f" | Block: {data['block']}"
        if data['floor'] is not None:
            hall_info += f" | Floor: {data['floor']}"
        ws.merge_cells('A3:D3')
        ws['A3'] = hall_info
        ws['A3'].alignment = Alignment(horizontal="center")

        # Headers (row 5)
        headers = ["Seat No.", "Register No.", "Student Name", "Department"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=5, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border

        # Data rows
        for row_idx, student in enumerate(data["students"], 6):
            ws.cell(row=row_idx, column=1, value=student["seat_number"]).border = thin_border
            ws.cell(row=row_idx, column=2, value=student["register_number"]).border = thin_border
            ws.cell(row=row_idx, column=3, value=student["full_name"]).border = thin_border
            ws.cell(row=row_idx, column=4, value=student["department"]).border = thin_border

        # Adjust column widths
        ws.column_dimensions['A'].width = 10
        ws.column_dimensions['B'].width = 18
        ws.column_dimensions['C'].width = 30
        ws.column_dimensions['D'].width = 25

    # Create summary sheet
    summary = wb.create_sheet(title="Summary", index=0)
    summary['A1'] = "Exam Seating Summary"
    summary['A1'].font = Font(bold=True, size=14)
    
    summary['A3'] = "Exam:"
    summary['B3'] = exam.title
    summary['A4'] = "Date:"
    summary['B4'] = str(exam.exam_date)
    summary['A5'] = "Time:"
    summary['B5'] = f"{exam.start_time} - {exam.end_time}"
    summary['A6'] = "Total Students:"
    summary['B6'] = len(rows)

    summary['A8'] = "Hall"
    summary['B8'] = "Students"
    summary['A8'].font = Font(bold=True)
    summary['B8'].font = Font(bold=True)

    for idx, (hall_name, data) in enumerate(halls_data.items(), 9):
        summary[f'A{idx}'] = hall_name
        summary[f'B{idx}'] = len(data["students"])

    summary.column_dimensions['A'].width = 30
    summary.column_dimensions['B'].width = 15

    # Save to bytes
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"seating_{exam.title.replace(' ', '_')}_{exam.exam_date}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
