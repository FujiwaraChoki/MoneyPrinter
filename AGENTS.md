# AGENTS Guide for MoneyPrinter

This file is the operating manual for coding agents working in this repository.
Follow it before making changes.

## 1) Repository Layout

- `Backend/`: Flask API, DB-backed job queue, and video generation pipeline.
- `Frontend/`: static HTML/JS client served by `python -m http.server`.
- `docs/`: source-of-truth setup and runtime docs.
- `fonts/`, `Songs/`, `subtitles/`, `temp/`: runtime assets/output folders.
- Root output artifact: `output.mp4`.

## 2) Source of Truth and Existing Rules

- No `.cursor/rules/` directory found.
- No `.cursorrules` file found.
- No `.github/copilot-instructions.md` file found.
- If any of the above appear later, treat them as higher-priority constraints and update this file.

## 3) Environment and Setup Commands

- Python version: `>=3.11` (from `pyproject.toml`).
- Dependency manager used in docs: `uv`.
- Create local env file: `cp .env.example .env`.
- Install dependencies: `uv sync`.
- Run backend: `uv run python Backend/main.py`.
- Run worker (new terminal): `uv run python Backend/worker.py`.
- Run frontend (new terminal): `python3 -m http.server 3000 --directory Frontend`.
- Docker workflow: `docker compose up --build`.

## 4) Build, Lint, and Test Commands

This project has a baseline `pytest` setup for backend repository tests.
Use the commands below as the expected agent workflow.

### 4.1 Build / Runtime Verification

- Backend syntax check: `uv run python -m compileall Backend`.
- Frontend syntax sanity (lightweight): open `Frontend/index.html` in browser and run generation flow.
- API smoke check after backend start: `curl http://localhost:8080/api/models`.
- Queue smoke check: `curl -X POST http://localhost:8080/api/generate -H "Content-Type: application/json" -d '{"videoSubject":"test","voice":"en_us_001","paragraphNumber":1,"customPrompt":""}'`.
- Full local run: backend + worker + frontend servers, then generate a short sample video.

### 4.2 Lint / Formatting (Recommended)

- There is no enforced formatter in-repo today.
- Follow existing style and keep diffs minimal.
- If linting is requested, prefer adding tooling in a separate PR.
- Suggested ad-hoc checks when available locally:
  - `uv run python -m py_compile Backend/*.py`
  - `uv run python -m compileall Backend`

### 4.3 Test Commands (Current and Future)

- Run all tests: `uv run pytest`
- Run one file: `uv run pytest tests/test_file.py`
- Run a single test: `uv run pytest tests/test_file.py::test_name`
- Run a single class test: `uv run pytest tests/test_file.py::TestClass::test_name`
- Current suite location: `tests/`.

## 5) High-Confidence Conventions from Existing Code

These conventions are inferred from current source and should guide new changes.

### 5.1 Python Imports

- Prefer standard library imports first, then third-party, then local modules.
- Use one import per line for readability in long modules.
- Avoid wildcard imports in new code (`from module import *`), even if legacy files use them.
- Prefer explicit local imports, e.g. `from utils import ENV_FILE, TEMP_DIR`.

### 5.2 Formatting and Structure

- Use 4-space indentation in Python.
- Keep line length readable; split long calls across multiple lines.
- Favor small helper functions for distinct pipeline stages.
- Keep side-effectful startup logic near application boot (`load_dotenv`, env checks).

### 5.3 Typing and Signatures

- Add type hints to all new/modified function signatures.
- Reuse `Optional`, `List`, `Tuple`, `dict` typing already used in backend.
- Prefer explicit return types (`-> str`, `-> None`, `-> Tuple[...]`).
- Use `Path` for filesystem paths where practical.

### 5.4 Naming Conventions

- Python functions/variables: `snake_case`.
- Constants/env keys: `UPPER_SNAKE_CASE`.
- JS variables/functions in frontend: `camelCase`.
- Keep API route names simple and verb-oriented (`/api/generate`, `/api/cancel`).

### 5.5 Error Handling and Logging

- Fail fast on missing critical env vars (current code exits early in startup checks).
- Catch exceptions at boundary layers (HTTP handlers, external API calls, file IO).
- Return user-safe JSON error messages from Flask endpoints.
- Log actionable context with existing logger/log-stream helpers.
- Do not swallow exceptions silently; at minimum emit error logs.

### 5.6 Filesystem and Path Safety

- Prefer `pathlib.Path` operations.
- Ensure directories exist before writing (`mkdir(parents=True, exist_ok=True)`).
- Sanitize uploaded filenames (`os.path.basename`) before save.
- Avoid hardcoded OS-specific paths; rely on env vars and `Path.resolve()`.

### 5.7 Backend API Patterns

- Keep endpoint payloads consistent with `{"status": "success|error", ...}`.
- Use appropriate HTTP status codes for conflict/client errors (e.g., `409`, `400`).
- Long-running work should run in worker process from DB queue, not on request thread.
- Preserve cancellation semantics using per-job cancellation and persisted job events.

### 5.8 Frontend Patterns

- Use centralized API helper (`apiRequest`) for backend calls.
- Validate required fields before firing requests.
- Keep user feedback explicit via toasts and status area toggles.
- Preserve localStorage key patterns (`<fieldId>Value`).

## 6) Change Scope Rules for Agents

- Make minimal, targeted edits.
- Do not rename files/modules unless required by task.
- Do not introduce new frameworks/toolchains without request.
- Keep backward compatibility for existing API payload shape when possible.
- Update docs in `docs/` when setup, env vars, or runtime behavior changes.

## 7) Validation Checklist Before Finishing

- Ran relevant command(s) from section 4.
- Confirmed backend still starts (`uv run python Backend/main.py`).
- Confirmed worker still starts (`uv run python Backend/worker.py`).
- Confirmed frontend still loads (`python3 -m http.server 3000 --directory Frontend`).
- Verified changed endpoints still return JSON and preserve `status` field.
- Checked no secrets were added to tracked files.

## 8) Notes for Future Tooling PRs

- Keep tests standardized on `pytest` and document exact paths/selectors here.
- If adding linting, prefer `ruff` for lint + format and commit config files.
- If adding type checks, document command and strictness level (`mypy` or equivalent).
- Keep this file updated whenever workflow commands change.

## 9) Agent Workflow Expectations

- Prefer minimal diffs and preserve current behavior unless the task requires changes.
- Keep API responses machine-parseable and consistent for frontend consumers.
- Avoid checking in generated media/output artifacts unless explicitly requested.
- Before returning work, include what was validated and what was not validated.
- When adding commands or tooling, update this file and `docs/` together.
