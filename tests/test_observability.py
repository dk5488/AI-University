import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.errors import DomainError


def test_request_id_middleware():
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert "X-Process-Time" in response.headers


def test_app_error_handler():
    # Setup a route that raises AppError for testing
    @app.get("/test-error")
    async def raise_error():
        raise DomainError("Test error", details={"key": "value"})

    client = TestClient(app)
    response = client.get("/test-error")
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "internal_error" # DomainError base code
    assert data["error"]["message"] == "Test error"
    assert data["error"]["details"] == {"key": "value"}
    assert "request_id" in data["error"]
