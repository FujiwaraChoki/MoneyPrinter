from repository import (
    claim_next_queued_job,
    create_job,
    list_job_events,
    mark_failed,
    mark_completed,
    mark_cancelled,
    request_cancel,
)


def test_create_job_persists_payload_and_queued_event(session):
    payload = {"videoSubject": "money basics", "paragraphNumber": 1}

    job = create_job(session, payload=payload)

    assert job.id
    assert job.status == "queued"
    assert job.payload == payload

    events = list_job_events(session, job.id)
    assert len(events) == 1
    assert events[0].event_type == "queued"
    assert events[0].message == "Job queued."


def test_request_cancel_cancels_queued_job_and_tracks_events(session):
    job = create_job(session, payload={"videoSubject": "cancel me"})

    cancelled = request_cancel(session, job.id)

    assert cancelled is True

    events = list_job_events(session, job.id)
    event_types = [event.event_type for event in events]
    assert "cancel_requested" in event_types
    assert "cancelled" in event_types


def test_claim_next_queued_job_marks_running_and_skips_cancelled(session):
    first_job = create_job(session, payload={"videoSubject": "first"})
    second_job = create_job(session, payload={"videoSubject": "second"})
    request_cancel(session, first_job.id)

    claimed_job = claim_next_queued_job(session)

    assert claimed_job is not None
    assert claimed_job.id == second_job.id
    assert claimed_job.status == "running"
    assert claimed_job.attempt_count == 1


def test_mark_completed_updates_status_and_emits_complete_event(session):
    job = create_job(session, payload={"videoSubject": "done"})
    running_job = claim_next_queued_job(session)
    assert running_job is not None

    mark_completed(session, job.id, result_path="/tmp/output.mp4")

    events = list_job_events(session, job.id)
    complete_events = [event for event in events if event.event_type == "complete"]
    assert len(complete_events) == 1
    assert complete_events[0].payload == {"path": "/tmp/output.mp4"}


def test_mark_failed_updates_error_message_and_event(session):
    job = create_job(session, payload={"videoSubject": "bad run"})

    mark_failed(session, job.id, error_message="render crash")

    events = list_job_events(session, job.id)
    assert events[-1].event_type == "error"
    assert events[-1].message == "render crash"


def test_mark_cancelled_sets_status_and_writes_cancelled_event(session):
    job = create_job(session, payload={"videoSubject": "stop"})

    mark_cancelled(session, job.id, reason="cancelled in worker")

    events = list_job_events(session, job.id)
    assert events[-1].event_type == "cancelled"
    assert events[-1].message == "cancelled in worker"
