from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class SeatAllocation(Base):
    """
    A student's physical seat assignment within a seating session.

    session_id is the anchor for seat-uniqueness (prevents double-booking
    the same physical seat even when different exams run simultaneously).
    exam_id is the student's specific exam (nullable — some session-level
    arrangements may not require per-student exam tracking).
    """
    __tablename__ = "seat_allocations"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(
        Integer, ForeignKey("exam_sessions.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    exam_id = Column(
        Integer, ForeignKey("exams.id", ondelete="SET NULL"),
        nullable=True, index=True       # student's specific exam (may differ per dept)
    )
    student_id = Column(
        Integer, ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    hall_id = Column(
        Integer, ForeignKey("exam_halls.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    seat_number = Column(Integer, nullable=False)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        # One seat per student per session
        UniqueConstraint("session_id", "student_id", name="uq_alloc_session_student"),
        # One student per physical seat per session (prevents double-booking)
        UniqueConstraint("session_id", "hall_id", "seat_number", name="uq_alloc_session_hall_seat"),
    )

    session = relationship("ExamSession", back_populates="seat_allocations")
    exam = relationship("Exam", back_populates="seat_allocations")
    student = relationship("Student", back_populates="seat_allocations")
    hall = relationship("ExamHall", back_populates="seat_allocations")
