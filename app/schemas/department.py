from pydantic import BaseModel, field_validator
from datetime import datetime


class DepartmentCreate(BaseModel):
    name: str
    code: str

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, v: str) -> str:
        return v.strip().upper()


class DepartmentResponse(BaseModel):
    id: int
    name: str
    code: str
    created_at: datetime

    model_config = {"from_attributes": True}
