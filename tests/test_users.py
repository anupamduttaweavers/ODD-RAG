"""Tests for user endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.v1.endpoints.users import fake_users_db, user_id_counter


@pytest.fixture
def client():
    """Create a test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_db():
    """Reset the fake database before each test."""
    global user_id_counter
    fake_users_db.clear()
    # Note: Can't reset global counter easily in module scope
    yield


def test_create_user(client):
    """Test creating a new user."""
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpass123",
    }
    response = client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["username"] == user_data["username"]
    assert "id" in data


def test_get_users(client):
    """Test getting all users."""
    # Create a user first
    user_data = {
        "email": "test2@example.com",
        "username": "testuser2",
        "password": "testpass123",
    }
    client.post("/api/v1/users/", json=user_data)
    
    response = client.get("/api/v1/users/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_user_not_found(client):
    """Test getting a non-existent user."""
    response = client.get("/api/v1/users/99999")
    assert response.status_code == 404
