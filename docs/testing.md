# Testing

MoneyPrinter uses `pytest` for backend tests.

## Install test dependencies

Install dev dependencies (includes `pytest`):

```bash
uv sync --group dev
```

## Run tests

Run all tests:

```bash
uv run pytest
```

Run one test file:

```bash
uv run pytest tests/test_repository.py
```

Run one test:

```bash
uv run pytest tests/test_repository.py::test_create_job_persists_payload_and_queued_event
```

## Current test scope

- `tests/test_api_jobs.py`: API queue, job status/events, and cancellation endpoints.
- `tests/test_api_misc.py`: API model listing fallback and song upload endpoint behavior.
- `tests/test_repository.py`: queue/repository behavior for create, claim, cancel, and completion events.
- `tests/test_worker.py`: worker loop behavior for success, cancellation, failure, and empty queue.
- `tests/test_utils.py`: filesystem cleanup, song selection, and ImageMagick binary resolution.
- `tests/conftest.py`: isolated SQLite session fixture per test.
