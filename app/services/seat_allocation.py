import random
from typing import Dict, List

from sqlalchemy.orm import Session

from app.models.exam import Exam
from app.models.exam_hall import ExamHall
from app.models.seat_allocation import SeatAllocation
from app.models.student import Student


def _interleave_by_department(students: List[Student]) -> List[Student]:
    """
    Round-robin interleave students grouped by department so that consecutive
    seats within a hall belong to different departments, reducing the chance
    of same-subject students sitting adjacent to each other.
    """
    dept_groups: Dict[int, List[Student]] = {}
    for s in students:
        dept_groups.setdefault(s.department_id, []).append(s)

    # Shuffle within each department group for randomness
    for group in dept_groups.values():
        random.shuffle(group)

    result: List[Student] = []
    queues = list(dept_groups.values())
    while queues:
        next_queues = []
        for q in queues:
            result.append(q.pop(0))
            if q:
                next_queues.append(q)
        queues = next_queues

    return result


def generate_seating(exam_id: int, db: Session) -> List[SeatAllocation]:
    """
    Generate seat allocations for a given exam.

    - Fetches all active students matching the exam's semester (and department
      if the exam is department-specific).
    - Distributes students across active halls in round-robin department order.
    - Seat numbers are sequential (1-based) within each hall.
    - Any existing allocations for the exam are replaced atomically.

    Raises ValueError for missing exam, no students, no halls, or insufficient capacity.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise ValueError(f"Exam with id {exam_id} not found")

    student_q = db.query(Student).filter(
        Student.is_active == True,  # noqa: E712
        Student.semester == exam.semester,
    )
    if exam.department_id:
        student_q = student_q.filter(Student.department_id == exam.department_id)
    students = student_q.all()

    if not students:
        raise ValueError("No active students found matching this exam's criteria")

    halls = (
        db.query(ExamHall)
        .filter(ExamHall.is_active == True)  # noqa: E712
        .order_by(ExamHall.id)
        .all()
    )
    if not halls:
        raise ValueError("No active exam halls are available")

    total_capacity = sum(h.capacity for h in halls)
    if len(students) > total_capacity:
        raise ValueError(
            f"Insufficient hall capacity. Students: {len(students)}, "
            f"total capacity: {total_capacity}"
        )

    # Remove any prior allocation for this exam (idempotent re-generation)
    db.query(SeatAllocation).filter(SeatAllocation.exam_id == exam_id).delete()

    distributed = _interleave_by_department(students)

    allocations: List[SeatAllocation] = []
    idx = 0
    for hall in halls:
        for seat_num in range(1, hall.capacity + 1):
            if idx >= len(distributed):
                break
            alloc = SeatAllocation(
                exam_id=exam_id,
                student_id=distributed[idx].id,
                hall_id=hall.id,
                seat_number=seat_num,  # Now an integer, not a string
            )
            db.add(alloc)
            allocations.append(alloc)
            idx += 1
        if idx >= len(distributed):
            break

    db.commit()
    return allocations
