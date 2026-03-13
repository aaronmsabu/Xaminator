"""
Tests for department endpoints.
"""
import pytest


class TestDepartmentEndpoints:
    """Test suite for /departments endpoints."""

    def test_create_department(self, client, auth_headers):
        """Test creating a department."""
        response = client.post(
            "/departments/",
            json={"name": "Computer Science", "code": "CSE"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Computer Science"
        assert data["code"] == "CSE"
        assert "id" in data

    def test_create_department_duplicate_code(self, client, auth_headers):
        """Test creating department with duplicate code fails."""
        client.post(
            "/departments/",
            json={"name": "Computer Science", "code": "CSE"},
            headers=auth_headers,
        )
        response = client.post(
            "/departments/",
            json={"name": "Different Name", "code": "CSE"},
            headers=auth_headers,
        )
        assert response.status_code == 400

    def test_list_departments(self, client, auth_headers):
        """Test listing departments."""
        # Create some departments
        client.post(
            "/departments/",
            json={"name": "Computer Science", "code": "CSE"},
            headers=auth_headers,
        )
        client.post(
            "/departments/",
            json={"name": "Electronics", "code": "ECE"},
            headers=auth_headers,
        )

        response = client.get("/departments/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_get_department(self, client, auth_headers):
        """Test getting a single department."""
        create_response = client.post(
            "/departments/",
            json={"name": "Computer Science", "code": "CSE"},
            headers=auth_headers,
        )
        dept_id = create_response.json()["id"]

        response = client.get(f"/departments/{dept_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["code"] == "CSE"

    def test_get_department_not_found(self, client, auth_headers):
        """Test getting non-existent department."""
        response = client.get("/departments/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_department_endpoints_require_auth(self, client):
        """Test that department endpoints require authentication."""
        response = client.get("/departments/")
        assert response.status_code == 403

        response = client.post("/departments/", json={"name": "Test", "code": "TST"})
        assert response.status_code == 403
