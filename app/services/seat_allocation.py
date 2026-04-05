"""
seat_allocation.py — Seating generation service

Supports two modes:
  1. Session-based (recommended): multiple (exam, students) batches share halls.
     Students from all batches are mixed together for anti-cheating.
     Seat uniqueness is guaranteed globally within the session.

  2. Legacy single-exam: kept for backward compatibility.
"""
import random
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.exam import Exam
from app.models.exam_session import ExamSession
from app.models.exam_hall import ExamHall
from app.models.exam_hall_availability import ExamHallAvailability
from app.models.seat_allocation import SeatAllocation
from app.models.student import Student


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _interleave_by_department(
    students_with_exam: List[Tuple[Student, Optional[int]]]
) -> List[Tuple[Student, Optional[int]]]:
    """
    Round-robin interleave (student, exam_id) pairs grouped by department so
    that consecutive seats belong to different departments (anti-cheating).
    """
    dept_groups: Dict[int, List[Tuple[Student, Optional[int]]]] = {}
    for student, exam_id in students_with_exam:
        dept_groups.setdefault(student.department_id, []).append((student, exam_id))

    for group in dept_groups.values():
        random.shuffle(group)

    result: List[Tuple[Student, Optional[int]]] = []
    queues = list(dept_groups.values())
    while queues:
        next_queues = []
        for q in queues:
            result.append(q.pop(0))
            if q:
                next_queues.append(q)
        queues = next_queues

    return result


# ─── Session-based seating (primary path) ────────────────────────────────────

def generate_session_seating(
    session_id: int,
    batches: List[Dict],   # [{"exam_id": int, "student_ids": [int, ...]}]
    hall_ids: List[int],
    db: Session,
) -> List[SeatAllocation]:
    """
    Generate seating for a full exam session.

    - batches: list of {exam_id, student_ids} — one entry per department/batch.
    - hall_ids: explicitly selected halls (must be active).
    - Students from all batches are mixed together (round-robin by department).
    - Each SeatAllocation carries session_id for global seat-uniqueness and
      exam_id for the individual student's exam subject.
    - Existing allocations for this session are cleared first (idempotent).

    Raises ValueError for missing session, no students, no halls, or
    insufficient capacity.
    """
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    if not session:
        raise ValueError(f"Exam session {session_id} not found")

    # Resolve students for each batch
    students_with_exam: List[Tuple[Student, Optional[int]]] = []
    seen_student_ids: set = set()

    for batch in batches:
        exam_id = batch.get("exam_id")   # may be None — that is valid
        raw_ids = list(dict.fromkeys(batch["student_ids"]))  # de-dup within batch

        batch_students = (
            db.query(Student)
            .filter(
                Student.id.in_(raw_ids),
                Student.is_active == True,  # noqa: E712
            )
            .all()
        )

        for s in batch_students:
            if s.id not in seen_student_ids:          # cross-batch de-dup
                students_with_exam.append((s, exam_id))
                seen_student_ids.add(s.id)

    if not students_with_exam:
        raise ValueError("No active students found in the provided batches")

    # Resolve halls
    if not hall_ids:
        raise ValueError("No halls specified for this session")

    halls = (
        db.query(ExamHall)
        .filter(
            ExamHall.id.in_(hall_ids),
            ExamHall.is_active == True,  # noqa: E712
        )
        .order_by(ExamHall.id)
        .all()
    )

    if not halls:
        raise ValueError("None of the specified halls are active")

    total_capacity = sum(h.capacity for h in halls)
    if len(students_with_exam) > total_capacity:
        raise ValueError(
            f"Insufficient capacity. Students: {len(students_with_exam)}, "
            f"available: {total_capacity}"
        )

    # Clear any prior allocations for this session
    db.query(SeatAllocation).filter(SeatAllocation.session_id == session_id).delete()

    # Interleave students by department
    distributed = _interleave_by_department(students_with_exam)

    allocations: List[SeatAllocation] = []
    idx = 0
    for hall in halls:
        for seat_num in range(1, hall.capacity + 1):
            if idx >= len(distributed):
                break
            student, exam_id = distributed[idx]
            alloc = SeatAllocation(
                session_id=session_id,
                exam_id=exam_id,
                student_id=student.id,
                hall_id=hall.id,
                seat_number=seat_num,
            )
            db.add(alloc)
            allocations.append(alloc)
            idx += 1
        if idx >= len(distributed):
            break

    db.commit()
    return allocations


# ─── Legacy single-exam seating (backward compat) ────────────────────────────

def generate_seating(
    exam_id: int,
    db: Session,
    student_ids: List[int] | None = None,
) -> List[SeatAllocation]:
    """
    LEGACY: Generate seating keyed to a single exam.

    This path is preserved for backward compatibility. New code should use
    generate_session_seating() instead, which properly handles multi-exam
    sessions without seat double-booking.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise ValueError(f"Exam {exam_id} not found")

    # If exam belongs to a session, delegate to session-based generation
    if exam.session_id:
        raise ValueError(
            "This exam belongs to an exam session. "
            "Use POST /generate-seating/session instead."
        )

    # Resolve students
    if student_ids is not None:
        unique_ids = list(dict.fromkeys(student_ids))
        students = (
            db.query(Student)
            .filter(Student.id.in_(unique_ids), Student.is_active == True)  # noqa: E712
            .all()
        )
    else:
        sq = db.query(Student).filter(
            Student.is_active == True,  # noqa: E712
            Student.semester == exam.semester,
        )
        if exam.department_id:
            sq = sq.filter(Student.department_id == exam.department_id)
        students = sq.all()

    if not students:
        raise ValueError("No active students found matching this exam's criteria")

    # Get available halls
    unavailable_ids = {
        row[0]
        for row in db.query(ExamHallAvailability.hall_id).filter(
            ExamHallAvailability.exam_id == exam_id,
            ExamHallAvailability.is_available == False,  # noqa: E712
        ).all()
    }
    halls = [
        h for h in db.query(ExamHall)
        .filter(ExamHall.is_active == True)  # noqa: E712
        .order_by(ExamHall.id).all()
        if h.id not in unavailable_ids
    ]

    if not halls:
        raise ValueError("No available exam halls for this exam")

    total_capacity = sum(h.capacity for h in halls)
    if len(students) > total_capacity:
        raise ValueError(
            f"Insufficient hall capacity. Students: {len(students)}, "
            f"total capacity: {total_capacity}"
        )

    # For the legacy path, we need a session.  Create a shadow session
    # automatically so the new constraint model is satisfied.
    shadow_session = ExamSession(
        title=f"[Auto] {exam.title}",
        exam_date=exam.exam_date,
        start_time=exam.start_time,
        end_time=exam.end_time,
        academic_year=exam.academic_year,
        status=exam.status,
    )
    db.add(shadow_session)
    db.flush()  # get the id

    # Wipe old allocations for this exam (legacy sessions won't have session_id)
    db.query(SeatAllocation).filter(SeatAllocation.exam_id == exam_id).delete()

    students_with_exam = [(s, exam_id) for s in students]
    distributed = _interleave_by_department(students_with_exam)

    allocations: List[SeatAllocation] = []
    idx = 0
    for hall in halls:
        for seat_num in range(1, hall.capacity + 1):
            if idx >= len(distributed):
                break
            student, eid = distributed[idx]
            alloc = SeatAllocation(
                session_id=shadow_session.id,
                exam_id=eid,
                student_id=student.id,
                hall_id=hall.id,
                seat_number=seat_num,
            )
            db.add(alloc)
            allocations.append(alloc)
            idx += 1
        if idx >= len(distributed):
            break

    db.commit()
    return allocations
