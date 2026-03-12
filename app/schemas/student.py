import re
from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional


class StudentCreate(BaseModel):
    register_number: str
    full_name: str
    email: Optional[EmailStr] = None
    department_id: int
    semester: int

    @field_validator("register_number")
    @classmethod
    def validate_register_number(cls, v: str) -> str:
        normalized = v.strip().upper()
        if not re.match(r"^[A-Z0-9]{5,20}$", normalized):
            raise ValueError("Register number must be 5–20 uppercase alphanumeric characters")
        return normalized

    @field_validator("semester")
    @classmethod
    def validate_semester(cls, v: int) -> int:
        if not 1 <= v <= 12:
            raise ValueError("Semester must be between 1 and 12")
        return v


class StudentUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    semester: Optional[int] = None
    is_active: Optional[bool] = None

    @field_validator("semester")
    @classmethod
    def validate_semester(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not 1 <= v <= 12:
            raise ValueError("Semester must be between 1 and 12")
        return v


class StudentResponse(BaseModel):
    id: int
    register_number: str
    full_name: str
    email: Optional[str]
    department_id: int
    semester: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
