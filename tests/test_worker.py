from repository import create_job, get_job, list_job_events
import worker


def _disable_cleanup(monkeypatch):
    monkeypatch.setattr(worker, "clean_dir", lambda _: None)


def test_process_next_job_returns_false_when_queue_is_empty(
    monkeypatch, session_factory
):
    monkeypatch.setattr(worker, "SessionLocal", session_factory)
    _disable_cleanup(monkeypatch)

    assert worker.process_next_job() is False


def test_process_next_job_marks_completed_on_pipeline_success(
    monkeypatch, session_factory
):
    with session_factory() as session:
        job = create_job(session, payload={"videoSubject": "worker success"})

    monkeypatch.setattr(worker, "SessionLocal", session_factory)
    _disable_cleanup(monkeypatch)

    def fake_pipeline(data, is_cancelled, on_log):
        assert data["videoSubject"] == "worker success"
        assert is_cancelled() is False
        on_log("pipeline started", "info")
        return "rendered.mp4"

    monkeypatch.setattr(worker, "run_generation_pipeline", fake_pipeline)

    assert worker.process_next_job() is True

    with session_factory() as session:
        updated_job = get_job(session, job.id)
        assert updated_job is not None
        assert updated_job.status == "completed"
        assert updated_job.result_path == "rendered.mp4"

        event_types = [event.event_type for event in list_job_events(session, job.id)]
        assert "running" in event_types
        assert "log" in event_types
        assert "complete" in event_types


def test_process_next_job_marks_cancelled_on_pipeline_cancelled(
    monkeypatch, session_factory
):
    with session_factory() as session:
        job = create_job(session, payload={"videoSubject": "worker cancelled"})

    monkeypatch.setattr(worker, "SessionLocal", session_factory)
    _disable_cleanup(monkeypatch)

    def fake_pipeline(*_args, **_kwargs):
        raise worker.PipelineCancelled("cancelled by user")

    monkeypatch.setattr(worker, "run_generation_pipeline", fake_pipeline)

    assert worker.process_next_job() is True

    with session_factory() as session:
        updated_job = get_job(session, job.id)
        assert updated_job is not None
        assert updated_job.status == "cancelled"

        events = list_job_events(session, job.id)
        assert events[-1].event_type == "cancelled"
        assert events[-1].message == "cancelled by user"


def test_process_next_job_marks_failed_on_pipeline_error(monkeypatch, session_factory):
    with session_factory() as session:
        job = create_job(session, payload={"videoSubject": "worker failure"})

    monkeypatch.setattr(worker, "SessionLocal", session_factory)
    _disable_cleanup(monkeypatch)

    def fake_pipeline(*_args, **_kwargs):
        raise RuntimeError("pipeline exploded")

    monkeypatch.setattr(worker, "run_generation_pipeline", fake_pipeline)

    assert worker.process_next_job() is True

    with session_factory() as session:
        updated_job = get_job(session, job.id)
        assert updated_job is not None
        assert updated_job.status == "failed"
        assert updated_job.error_message == "pipeline exploded"

        events = list_job_events(session, job.id)
        assert events[-1].event_type == "error"
        assert events[-1].message == "pipeline exploded"


def test_job_cancelled_helper_returns_true_for_missing_job(
    monkeypatch, session_factory
):
    monkeypatch.setattr(worker, "SessionLocal", session_factory)

    assert worker._job_cancelled("missing-job-id") is True


def test_job_cancelled_helper_reflects_cancel_flag(monkeypatch, session_factory):
    with session_factory() as session:
        job = create_job(session, payload={"videoSubject": "cancel-check"})

    monkeypatch.setattr(worker, "SessionLocal", session_factory)

    assert worker._job_cancelled(job.id) is False

    with session_factory() as session:
        job_to_update = get_job(session, job.id)
        assert job_to_update is not None
        job_to_update.cancel_requested = True
        session.commit()

    assert worker._job_cancelled(job.id) is True


def test_log_event_helper_persists_log_event(monkeypatch, session_factory):
    with session_factory() as session:
        job = create_job(session, payload={"videoSubject": "log-check"})

    monkeypatch.setattr(worker, "SessionLocal", session_factory)

    worker._log_event(job.id, "hello event", "warning")

    with session_factory() as session:
        events = list_job_events(session, job.id)
        assert events[-1].event_type == "log"
        assert events[-1].level == "warning"
        assert events[-1].message == "hello event"
