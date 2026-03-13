"""
Tests for student endpoints.
"""
import pytest


class TestStudentEndpoints:
    """Test suite for /students endpoints."""

    @pytest.fixture
    def department(self, client, auth_headers):
        """Create a test department."""
        response = client.post(
            "/departments/",
            json={"name": "Computer Science", "code": "CSE"},
            headers=auth_headers,
        )
        return response.json()

    def test_create_student(self, client, auth_headers, department):
        """Test creating a student."""
        response = client.post(
            "/students/",
            json={
                "register_number": "CSE2024001",
                "full_name": "John Doe",
                "email": "john@test.com",
                "department_id": department["id"],
                "semester": 4,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["register_number"] == "CSE2024001"
        assert data["full_name"] == "John Doe"
        assert data["is_active"] is True

    def test_create_student_duplicate_register(self, client, auth_headers, department):
        """Test creating student with duplicate register number fails."""
        client.post(
            "/students/",
            json={
                "register_number": "CSE2024001",
                "full_name": "John Doe",
                "department_id": department["id"],
                "semester": 4,
            },
            headers=auth_headers,
        )
        response = client.post(
            "/students/",
            json={
                "register_number": "CSE2024001",
                "full_name": "Jane Doe",
                "department_id": department["id"],
                "semester": 4,
            },
            headers=auth_headers,
        )
        assert response.status_code == 400

    def test_list_students_with_search(self, client, auth_headers, department):
        """Test listing students with search filter."""
        # Create students
        client.post(
            "/students/",
            json={
                "register_number": "CSE2024001",
                "full_name": "John Doe",
                "department_id": department["id"],
                "semester": 4,
            },
            headers=auth_headers,
        )
        client.post(
            "/students/",
            json={
                "register_number": "CSE2024002",
                "full_name": "Jane Smith",
                "department_id": department["id"],
                "semester": 4,
            },
            headers=auth_headers,
        )

        # Search by name
        response = client.get("/students/?search=John", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["full_name"] == "John Doe"

        # Search by register number
        response = client.get("/students/?search=CSE2024002", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["register_number"] == "CSE2024002"

    def test_list_students_with_pagination(self, client, auth_headers, department):
        """Test listing students with pagination."""
        # Create multiple students
        for i in range(5):
            client.post(
                "/students/",
                json={
                    "register_number": f"CSE202400{i}",
                    "full_name": f"Student {i}",
                    "department_id": department["id"],
                    "semester": 4,
                },
                headers=auth_headers,
            )

        # Test pagination
        response = client.get("/students/?skip=0&limit=2", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

        response = client.get("/students/?skip=2&limit=2", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_update_student(self, client, auth_headers, department):
        """Test updating a student."""
        create_response = client.post(
            "/students/",
            json={
                "register_number": "CSE2024001",
                "full_name": "John Doe",
                "department_id": department["id"],
                "semester": 4,
            },
            headers=auth_headers,
        )
        student_id = create_response.json()["id"]

        response = client.patch(
            f"/students/{student_id}",
            json={"full_name": "John Updated", "semester": 5},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["full_name"] == "John Updated"
        assert response.json()["semester"] == 5

    def test_delete_student(self, client, auth_headers, department):
        """Test deleting a student."""
        create_response = client.post(
            "/students/",
            json={
                "register_number": "CSE2024001",
                "full_name": "John Doe",
                "department_id": department["id"],
                "semester": 4,
            },
            headers=auth_headers,
        )
        student_id = create_response.json()["id"]

        response = client.delete(f"/students/{student_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify deletion
        response = client.get(f"/students/{student_id}", headers=auth_headers)
        assert response.status_code == 404
