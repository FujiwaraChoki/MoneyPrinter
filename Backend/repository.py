from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import and_, select, text
from sqlalchemy.orm import Session

from models import GenerationEvent, GenerationJob


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_job(session: Session, payload: dict, max_attempts: int = 1) -> GenerationJob:
    job = GenerationJob(
        id=str(uuid4()),
        status="queued",
        payload=payload,
        max_attempts=max_attempts,
        cancel_requested=False,
    )
    session.add(job)
    session.flush()
    append_event(session, job.id, "queued", "info", "Job queued.")
    session.commit()
    session.refresh(job)
    return job


def append_event(
    session: Session,
    job_id: str,
    event_type: str,
    level: str,
    message: str,
    payload: Optional[dict] = None,
) -> GenerationEvent:
    event = GenerationEvent(
        job_id=job_id,
        event_type=event_type,
        level=level,
        message=message,
        payload=payload,
    )
    session.add(event)
    session.flush()
    return event


def get_job(session: Session, job_id: str) -> Optional[GenerationJob]:
    return session.get(GenerationJob, job_id)


def list_job_events(
    session: Session, job_id: str, after_id: int = 0, limit: int = 200
) -> list[GenerationEvent]:
    stmt = (
        select(GenerationEvent)
        .where(
            and_(
                GenerationEvent.job_id == job_id,
                GenerationEvent.id > after_id,
            )
        )
        .order_by(GenerationEvent.id.asc())
        .limit(limit)
    )
    return list(session.scalars(stmt).all())


def request_cancel(session: Session, job_id: str) -> bool:
    job = get_job(session, job_id)
    if not job:
        return False

    if job.status in ("completed", "failed", "cancelled"):
        return True

    job.cancel_requested = True
    job.updated_at = utcnow()
    append_event(
        session, job.id, "cancel_requested", "warning", "Cancellation requested."
    )

    if job.status == "queued":
        job.status = "cancelled"
        job.completed_at = utcnow()
        append_event(
            session, job.id, "cancelled", "warning", "Job cancelled before execution."
        )

    session.commit()
    return True


def claim_next_queued_job(session: Session) -> Optional[GenerationJob]:
    dialect = session.bind.dialect.name if session.bind else ""

    if dialect == "postgresql":
        row = session.execute(
            text(
                """
                SELECT id
                FROM generation_jobs
                WHERE status = 'queued' AND cancel_requested = false
                ORDER BY created_at ASC
                FOR UPDATE SKIP LOCKED
                LIMIT 1
                """
            )
        ).first()
        if not row:
            return None
        job = get_job(session, row[0])
    else:
        stmt = (
            select(GenerationJob)
            .where(
                and_(
                    GenerationJob.status == "queued",
                    GenerationJob.cancel_requested.is_(False),
                )
            )
            .order_by(GenerationJob.created_at.asc())
            .limit(1)
        )
        job = session.scalars(stmt).first()

    if not job:
        return None

    job.status = "running"
    job.attempt_count = (job.attempt_count or 0) + 1
    job.started_at = utcnow()
    job.updated_at = utcnow()
    append_event(session, job.id, "running", "info", "Job started.")
    session.commit()
    session.refresh(job)
    return job


def mark_completed(session: Session, job_id: str, result_path: str) -> None:
    job = get_job(session, job_id)
    if not job:
        return
    job.status = "completed"
    job.result_path = result_path
    job.error_message = None
    job.completed_at = utcnow()
    job.updated_at = utcnow()
    append_event(
        session,
        job.id,
        "complete",
        "success",
        "Video generated successfully.",
        {"path": result_path},
    )
    session.commit()


def mark_cancelled(
    session: Session, job_id: str, reason: str = "Job cancelled."
) -> None:
    job = get_job(session, job_id)
    if not job:
        return
    job.status = "cancelled"
    job.completed_at = utcnow()
    job.updated_at = utcnow()
    append_event(session, job.id, "cancelled", "warning", reason)
    session.commit()


def mark_failed(session: Session, job_id: str, error_message: str) -> None:
    job = get_job(session, job_id)
    if not job:
        return
    job.status = "failed"
    job.error_message = error_message
    job.completed_at = utcnow()
    job.updated_at = utcnow()
    append_event(session, job.id, "error", "error", error_message)
    session.commit()
