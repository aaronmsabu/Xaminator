"""
Tests for authentication endpoints.
"""
import pytest


class TestAuthEndpoints:
    """Test suite for /auth endpoints."""

    def test_login_success(self, client, admin_user):
        """Test successful login."""
        response = client.post(
            "/auth/login",
            json={"username": "testadmin", "password": "testpassword"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, admin_user):
        """Test login with wrong password."""
        response = client.post(
            "/auth/login",
            json={"username": "testadmin", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user."""
        response = client.post(
            "/auth/login",
            json={"username": "nonexistent", "password": "password"},
        )
        assert response.status_code == 401

    def test_get_current_user(self, client, auth_headers, admin_user):
        """Test getting current user info."""
        response = client.get("/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testadmin"
        assert data["email"] == "admin@test.com"
        assert data["role"] == "admin"

    def test_get_current_user_no_auth(self, client):
        """Test getting current user without authentication."""
        response = client.get("/auth/me")
        assert response.status_code == 403  # No auth header
