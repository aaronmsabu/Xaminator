from pydantic import BaseModel
from datetime import datetime
from typing import List


class GenerateSeatingRequest(BaseModel):
    exam_id: int


class SeatAllocationResponse(BaseModel):
    id: int
    exam_id: int
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


class SeatingResponse(BaseModel):
    exam_id: int
    total_allocated: int
    allocations: List[SeatAllocationDetail]
