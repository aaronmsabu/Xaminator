from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class SeatAllocation(Base):
    __tablename__ = "seat_allocations"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(
        Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id = Column(
        Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    hall_id = Column(
        Integer, ForeignKey("exam_halls.id", ondelete="CASCADE"), nullable=False, index=True
    )
    seat_number = Column(String(20), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("exam_id", "student_id", name="uq_allocation_exam_student"),
        UniqueConstraint("exam_id", "hall_id", "seat_number", name="uq_allocation_hall_seat"),
    )

    exam = relationship("Exam", back_populates="seat_allocations")
    student = relationship("Student", back_populates="seat_allocations")
    hall = relationship("ExamHall", back_populates="seat_allocations")
