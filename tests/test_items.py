"""Tests for item endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.v1.endpoints.folder_management import fake_items_db


@pytest.fixture
def client():
    """Create a test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_db():
    """Reset the fake database before each test."""
    fake_items_db.clear()
    yield


def test_create_item(client):
    """Test creating a new item."""
    item_data = {
        "name": "Test Item",
        "description": "A test item",
        "price": 9.99,
    }
    response = client.post("/api/v1/items/", json=item_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == item_data["name"]
    assert data["price"] == item_data["price"]
    assert "id" in data


def test_get_items(client):
    """Test getting all items."""
    # Create an item first
    item_data = {
        "name": "Test Item",
        "description": "A test item",
        "price": 9.99,
    }
    client.post("/api/v1/items/", json=item_data)
    
    response = client.get("/api/v1/items/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_item_not_found(client):
    """Test getting a non-existent item."""
    response = client.get("/api/v1/items/99999")
    assert response.status_code == 404
