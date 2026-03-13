from sqlalchemy import Column, Integer, Boolean, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ExamHallAvailability(Base):
    """
    Tracks per-exam hall availability.
    
    If no record exists for an (exam_id, hall_id) pair, the hall is considered
    available by default (backward-compatible behavior).
    
    When is_available=False, the hall is excluded from seat allocation for that exam.
    """
    __tablename__ = "exam_hall_availability"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(
        Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    hall_id = Column(
        Integer, ForeignKey("exam_halls.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_available = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Ensure one availability record per exam-hall pair
    __table_args__ = (
        UniqueConstraint("exam_id", "hall_id", name="uq_exam_hall_availability"),
    )

    exam = relationship("Exam", backref="hall_availabilities")
    hall = relationship("ExamHall", backref="exam_availabilities")
