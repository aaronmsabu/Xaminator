from sqlalchemy import Column, Integer, String, Date, Time, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ExamSession(Base):
    """
    Represents a physical seating event — one time-slot in which multiple
    department-specific exams are held simultaneously in shared halls.

    Multiple Exam records (one per department) link to the same ExamSession.
    SeatAllocations are keyed by session_id to guarantee no two students
    share the same physical seat within the same session.
    """
    __tablename__ = "exam_sessions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)       # e.g. "Nov 2025 End Sem — Day 1, 9AM"
    exam_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    academic_year = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="scheduled", index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    exams = relationship("Exam", back_populates="session")
    seat_allocations = relationship("SeatAllocation", back_populates="session")
