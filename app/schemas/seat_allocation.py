from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


# ─── Legacy single-exam request (kept for backward compat) ───────────────────
class GenerateSeatingRequest(BaseModel):
    exam_id: int
    student_ids: Optional[List[int]] = None


# ─── Session-based request ────────────────────────────────────────────────────
class BatchSeatingInput(BaseModel):
    exam_id: int
    student_ids: List[int]


class GenerateSessionSeatingRequest(BaseModel):
    session_id: int
    hall_ids: List[int]
    batches: List[BatchSeatingInput]


# ─── Response models ──────────────────────────────────────────────────────────
class SeatAllocationResponse(BaseModel):
    id: int
    session_id: int
    exam_id: Optional[int]
    student_id: int
    hall_id: int
    seat_number: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SeatAllocationDetail(BaseModel):
    """Enriched allocation row with human-readable names."""
    id: int
    seat_number: int
    hall_name: str
    student_name: str
    register_number: str
    department_name: str
    exam_title: Optional[str] = None   # the student's specific exam subject


class SeatingResponse(BaseModel):
    session_id: int
    total_allocated: int
    allocations: List[SeatAllocationDetail]
