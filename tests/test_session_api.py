from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app


def test_session_api_lifecycle() -> None:
    client = TestClient(create_app())
    user_id = uuid4()

    start_response = client.post(
        f"/api/v1/users/{user_id}/sessions",
        json={
            "subject_code": "polity",
            "topic_slug": "fundamental-rights",
            "ttl_seconds": 300,
        },
    )

    assert start_response.status_code == 201
    started_session = start_response.json()
    assert started_session["user_id"] == str(user_id)
    assert started_session["subject_code"] == "polity"
    assert started_session["topic_slug"] == "fundamental-rights"
    assert started_session["time_spent_seconds"] == 0

    session_id = started_session["session_id"]

    get_response = client.get(f"/api/v1/users/{user_id}/sessions/{session_id}")

    assert get_response.status_code == 200
    assert get_response.json()["session_id"] == session_id

    end_response = client.delete(f"/api/v1/users/{user_id}/sessions/{session_id}")

    assert end_response.status_code == 200
    assert end_response.json()["session_id"] == session_id

    missing_response = client.get(f"/api/v1/users/{user_id}/sessions/{session_id}")

    assert missing_response.status_code == 404
