import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app


def test_user_dashboard():
    client = TestClient(app)
    user_id = uuid4()
    
    response = client.get(f"/api/v1/users/{user_id}/dashboard")
    
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(user_id)
    assert "progress" in data
    assert "due_revisions" in data
    assert "available_subjects" in data
    assert len(data["available_subjects"]) == 1
    assert data["available_subjects"][0]["code"] == "polity"
