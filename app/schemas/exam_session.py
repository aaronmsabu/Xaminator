from pydantic import BaseModel, field_validator
from datetime import date, time, datetime
from typing import List, Optional


class ExamSessionCreate(BaseModel):
    title: str
    exam_date: date
    start_time: time
    end_time: time
    academic_year: str

    @field_validator('end_time')
    @classmethod
    def end_after_start(cls, v, info):
        if 'start_time' in info.data and v <= info.data['start_time']:
            raise ValueError('end_time must be after start_time')
        return v


class ExamSessionResponse(BaseModel):
    id: int
    title: str
    exam_date: date
    start_time: time
    end_time: time
    academic_year: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class BatchSeatingInput(BaseModel):
    """One (exam, student list) pair for a multi-exam seating session."""
    exam_id: int
    student_ids: List[int]


class GenerateSessionSeatingRequest(BaseModel):
    """
    Request to generate seating for a full session.
    Batches map each department exam to its student IDs.
    hall_ids are the halls available for this session.
    """
    session_id: int
    hall_ids: List[int]
    batches: List[BatchSeatingInput]
