from sqlalchemy import Column, Integer, SmallInteger, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    register_number = Column(String(30), nullable=False, unique=True, index=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(255), unique=True)
    department_id = Column(
        Integer, ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    semester = Column(SmallInteger, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    department = relationship("Department", back_populates="students")
    seat_allocations = relationship("SeatAllocation", back_populates="student")
