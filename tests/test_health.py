from fastapi.testclient import TestClient

from app.main import create_app


def test_root_returns_service_metadata() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "AI University",
        "version": "0.1.0",
        "status": "ok",
    }


def test_health_check_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
