from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional


class ExamHallCreate(BaseModel):
    name: str
    block: Optional[str] = None
    floor: Optional[int] = None
    capacity: int

    @field_validator("capacity")
    @classmethod
    def validate_capacity(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Capacity must be greater than 0")
        return v


class ExamHallResponse(BaseModel):
    id: int
    name: str
    block: Optional[str]
    floor: Optional[int]
    capacity: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
