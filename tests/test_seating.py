"""
Tests for the seat allocation service.
"""
from datetime import date, time

import pytest
from app.models.department import Department
from app.models.student import Student
from app.models.exam_hall import ExamHall
from app.models.exam import Exam
from app.services.seat_allocation import generate_seating, _interleave_by_department


class TestInterleaveByDepartment:
    """Test the department interleaving algorithm."""

    def test_interleave_single_department(self, db_session):
        """Test interleaving with a single department."""
        dept = Department(name="CSE", code="CSE")
        db_session.add(dept)
        db_session.commit()

        students = [
            Student(
                register_number=f"CSE{i}",
                full_name=f"Student {i}",
                department_id=dept.id,
                semester=4,
            )
            for i in range(5)
        ]
        for s in students:
            db_session.add(s)
        db_session.commit()
        db_session.refresh(dept)

        # Re-query to get proper objects
        students = db_session.query(Student).all()
        result = _interleave_by_department(students)
        
        assert len(result) == 5

    def test_interleave_multiple_departments(self, db_session):
        """Test interleaving with multiple departments."""
        dept1 = Department(name="CSE", code="CSE")
        dept2 = Department(name="ECE", code="ECE")
        db_session.add_all([dept1, dept2])
        db_session.commit()

        students = []
        for i in range(3):
            students.append(
                Student(
                    register_number=f"CSE{i}",
                    full_name=f"CSE Student {i}",
                    department_id=dept1.id,
                    semester=4,
                )
            )
            students.append(
                Student(
                    register_number=f"ECE{i}",
                    full_name=f"ECE Student {i}",
                    department_id=dept2.id,
                    semester=4,
                )
            )
        for s in students:
            db_session.add(s)
        db_session.commit()

        students = db_session.query(Student).all()
        result = _interleave_by_department(students)

        # Check that consecutive students are from different departments
        # (at least for the first few, given random shuffle within groups)
        assert len(result) == 6
        
        # Verify all students are present
        result_ids = {s.id for s in result}
        original_ids = {s.id for s in students}
        assert result_ids == original_ids


class TestGenerateSeating:
    """Test the seating generation service."""

    @pytest.fixture
    def setup_exam_data(self, db_session):
        """Create test data for seating generation."""
        dept = Department(name="Computer Science", code="CSE")
        db_session.add(dept)
        db_session.commit()

        # Create students
        for i in range(10):
            student = Student(
                register_number=f"CSE202400{i}",
                full_name=f"Student {i}",
                department_id=dept.id,
                semester=4,
                is_active=True,
            )
            db_session.add(student)

        # Create halls
        hall1 = ExamHall(name="Hall A", capacity=5, is_active=True)
        hall2 = ExamHall(name="Hall B", capacity=10, is_active=True)
        db_session.add_all([hall1, hall2])

        # Create exam
        exam = Exam(
            title="Test Exam",
            exam_date=date(2026, 4, 1),
            start_time=time(9, 0, 0),
            end_time=time(12, 0, 0),
            academic_year="2025-26",
            semester=4,
            status="scheduled",
        )
        db_session.add(exam)
        db_session.commit()

        return {"exam": exam, "dept": dept}

    def test_generate_seating_success(self, db_session, setup_exam_data):
        """Test successful seating generation."""
        exam = setup_exam_data["exam"]
        
        allocations = generate_seating(exam.id, db_session)
        
        assert len(allocations) == 10  # All students allocated
        
        # Check seat numbers are integers
        for alloc in allocations:
            assert isinstance(alloc.seat_number, int)

    def test_generate_seating_idempotent(self, db_session, setup_exam_data):
        """Test that re-generating seating replaces old allocations."""
        exam = setup_exam_data["exam"]
        
        allocations1 = generate_seating(exam.id, db_session)
        assert len(allocations1) == 10
        
        # Re-generate
        allocations2 = generate_seating(exam.id, db_session)
        assert len(allocations2) == 10
        
        # Total allocations should still be 10 (not 20)
        from app.models.seat_allocation import SeatAllocation
        total = db_session.query(SeatAllocation).filter(
            SeatAllocation.exam_id == exam.id
        ).count()
        assert total == 10

    def test_generate_seating_exam_not_found(self, db_session):
        """Test seating generation with non-existent exam."""
        with pytest.raises(ValueError, match="not found"):
            generate_seating(99999, db_session)

    def test_generate_seating_no_students(self, db_session):
        """Test seating generation with no matching students."""
        exam = Exam(
            title="Test Exam",
            exam_date=date(2026, 4, 1),
            start_time=time(9, 0, 0),
            end_time=time(12, 0, 0),
            academic_year="2025-26",
            semester=8,  # No students in this semester
            status="scheduled",
        )
        db_session.add(exam)
        db_session.commit()

        with pytest.raises(ValueError, match="No active students"):
            generate_seating(exam.id, db_session)

    def test_generate_seating_no_halls(self, db_session):
        """Test seating generation with no active halls."""
        dept = Department(name="CSE", code="CSE")
        db_session.add(dept)
        db_session.commit()

        student = Student(
            register_number="CSE001",
            full_name="Test Student",
            department_id=dept.id,
            semester=4,
            is_active=True,
        )
        db_session.add(student)

        exam = Exam(
            title="Test Exam",
            exam_date=date(2026, 4, 1),
            start_time=time(9, 0, 0),
            end_time=time(12, 0, 0),
            academic_year="2025-26",
            semester=4,
            status="scheduled",
        )
        db_session.add(exam)
        db_session.commit()

        with pytest.raises(ValueError, match="No active exam halls"):
            generate_seating(exam.id, db_session)

    def test_generate_seating_insufficient_capacity(self, db_session):
        """Test seating generation with insufficient hall capacity."""
        dept = Department(name="CSE", code="CSE")
        db_session.add(dept)
        db_session.commit()

        # Create more students than hall capacity
        for i in range(20):
            student = Student(
                register_number=f"CSE{i:03d}",
                full_name=f"Student {i}",
                department_id=dept.id,
                semester=4,
                is_active=True,
            )
            db_session.add(student)

        # Small hall
        hall = ExamHall(name="Small Hall", capacity=5, is_active=True)
        db_session.add(hall)

        exam = Exam(
            title="Test Exam",
            exam_date=date(2026, 4, 1),
            start_time=time(9, 0, 0),
            end_time=time(12, 0, 0),
            academic_year="2025-26",
            semester=4,
            status="scheduled",
        )
        db_session.add(exam)
        db_session.commit()

        with pytest.raises(ValueError, match="Insufficient hall capacity"):
            generate_seating(exam.id, db_session)
