from sqlalchemy import Column, Integer, SmallInteger, String, Date, Time, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    exam_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    academic_year = Column(String(20), nullable=False)
    semester = Column(SmallInteger, nullable=False)
    department_id = Column(
        Integer, ForeignKey("departments.id", ondelete="SET NULL"), index=True
    )
    session_id = Column(
        Integer, ForeignKey("exam_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status = Column(String(20), nullable=False, default="scheduled", index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    department = relationship("Department", back_populates="exams")
    session = relationship("ExamSession", back_populates="exams")
    seat_allocations = relationship("SeatAllocation", back_populates="exam")
