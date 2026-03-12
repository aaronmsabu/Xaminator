from sqlalchemy import Column, Integer, SmallInteger, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ExamHall(Base):
    __tablename__ = "exam_halls"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    block = Column(String(50))
    floor = Column(SmallInteger)
    capacity = Column(SmallInteger, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    seat_allocations = relationship("SeatAllocation", back_populates="hall")
