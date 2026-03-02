import os

import pytest

from repository import append_event, create_job, get_job, list_job_events


os.environ.setdefault("PEXELS_API_KEY", "test-key")
os.environ.setdefault("TIKTOK_SESSION_ID", "test-session")
os.environ.setdefault("IMAGEMAGICK_BINARY", "/bin/echo")
os.environ.setdefault("DATABASE_URL", "sqlite:///moneyprinter_api_bootstrap.db")

import main


@pytest.fixture
def client(monkeypatch, session_factory):
    monkeypatch.setattr(main, "SessionLocal", session_factory)
    return main.app.test_client()


def test_generate_requires_video_subject(client):
    response = client.post("/api/generate", json={})

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["status"] == "error"
    assert payload["message"] == "videoSubject is required."


def test_generate_creates_job_and_job_status_is_fetchable(client):
    response = client.post(
        "/api/generate",
        json={
            "videoSubject": "api queue test",
            "paragraphNumber": 1,
            "customPrompt": "",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "success"
    assert payload["message"] == "Video generation queued."

    job_id = payload["jobId"]
    job_response = client.get(f"/api/jobs/{job_id}")
    job_payload = job_response.get_json()

    assert job_response.status_code == 200
    assert job_payload["status"] == "success"
    assert job_payload["job"]["id"] == job_id
    assert job_payload["job"]["state"] == "queued"


def test_get_events_respects_after_query_parameter(client, session_factory):
    with session_factory() as session:
        job = create_job(session, payload={"videoSubject": "events"})
        first_event = list_job_events(session, job.id)[0]
        append_event(session, job.id, "log", "info", "step 2")
        append_event(session, job.id, "log", "info", "step 3")
        session.commit()

    response = client.get(f"/api/jobs/{job.id}/events?after={first_event.id}")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "success"
    assert len(payload["events"]) == 2
    assert payload["events"][0]["message"] == "step 2"
    assert payload["events"][1]["message"] == "step 3"


def test_cancel_job_endpoint_cancels_existing_job(client, session_factory):
    with session_factory() as session:
        job = create_job(session, payload={"videoSubject": "cancel endpoint"})

    response = client.post(f"/api/jobs/{job.id}/cancel")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "success"
    assert payload["message"] == "Cancellation requested."

    with session_factory() as session:
        updated_job = get_job(session, job.id)
        assert updated_job is not None
        assert updated_job.status == "cancelled"
        assert updated_job.cancel_requested is True


def test_cancel_job_endpoint_returns_404_for_unknown_job(client):
    response = client.post("/api/jobs/missing-id/cancel")

    assert response.status_code == 404
    payload = response.get_json()
    assert payload["status"] == "error"
    assert payload["message"] == "Job not found."


def test_cancel_latest_running_job_returns_404_when_no_active_job(client):
    response = client.post("/api/cancel")

    assert response.status_code == 404
    payload = response.get_json()
    assert payload["status"] == "error"
    assert payload["message"] == "No active job found."


def test_cancel_latest_running_job_cancels_active_job(client, session_factory):
    with session_factory() as session:
        older_job = create_job(session, payload={"videoSubject": "older"})
        newer_job = create_job(session, payload={"videoSubject": "newer"})

    response = client.post("/api/cancel")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "success"
    assert payload["message"] == "Cancellation requested."
    assert payload["jobId"] in {older_job.id, newer_job.id}

    with session_factory() as session:
        older = get_job(session, older_job.id)
        newer = get_job(session, newer_job.id)
        assert older is not None
        assert newer is not None
        cancelled_count = int(older.cancel_requested) + int(newer.cancel_requested)
        assert cancelled_count == 1
