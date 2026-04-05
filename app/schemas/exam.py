from pydantic import BaseModel, field_validator, model_validator
from datetime import datetime, date, time
from typing import Optional

_VALID_STATUSES = {"scheduled", "ongoing", "completed", "cancelled"}


class ExamCreate(BaseModel):
    title: str
    exam_date: date
    start_time: time
    end_time: time
    academic_year: str
    semester: int
    department_id: Optional[int] = None
    session_id: Optional[int] = None

    @field_validator("semester")
    @classmethod
    def validate_semester(cls, v: int) -> int:
        if not 1 <= v <= 12:
            raise ValueError("Semester must be between 1 and 12")
        return v

    @model_validator(mode="after")
    def validate_times(self) -> "ExamCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class ExamStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in _VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(_VALID_STATUSES)}")
        return v


class ExamResponse(BaseModel):
    id: int
    title: str
    exam_date: date
    start_time: time
    end_time: time
    academic_year: str
    semester: int
    department_id: Optional[int]
    session_id: Optional[int] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
