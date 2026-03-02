# Architecture

MoneyPrinter now uses a database-backed queue architecture designed for reliability, restart safety, and future scaling.

## Overview

- `Frontend` submits generation requests and polls job status/events.
- `API (Flask)` validates input and enqueues jobs in Postgres.
- `Worker` claims queued jobs and runs the generation pipeline.
- `Postgres` is the source of truth for job state, progress events, and artifacts.

```mermaid
flowchart LR
    U[User] --> F[Frontend\nindex.html + app.js]
    F -->|POST /api/generate| A[API\nBackend/main.py]
    F -->|GET /api/jobs/:id| A
    F -->|GET /api/jobs/:id/events| A
    F -->|POST /api/jobs/:id/cancel| A

    A -->|insert job| DB[(Postgres)]
    A -->|read status/events| DB

    W[Worker\nBackend/worker.py] -->|claim queued job| DB
    W -->|write logs/events| DB
    W -->|update final state| DB
    W --> P[Pipeline\nBackend/pipeline.py]
    P --> FS[(temp/subtitles/output files)]
```

## Runtime Services (Docker)

```mermaid
flowchart TB
    subgraph Compose
      FE[frontend]
      API[backend]
      WK[worker]
      PG[(postgres)]
    end

    FE --> API
    API --> PG
    WK --> PG
    WK --> API
```

## Generation Lifecycle

```mermaid
stateDiagram-v2
    [*] --> queued
    queued --> running: worker claims job
    queued --> cancelled: cancel before claim
    running --> completed: success
    running --> failed: unrecoverable error
    running --> cancelled: cancellation requested
    completed --> [*]
    failed --> [*]
    cancelled --> [*]
```

## API + Worker Sequence

```mermaid
sequenceDiagram
    participant UI as Frontend
    participant API as Flask API
    participant DB as Postgres
    participant WK as Worker
    participant PL as Pipeline

    UI->>API: POST /api/generate
    API->>DB: INSERT generation_jobs(status=queued)
    API-->>UI: { status: success, jobId }

    loop Polling
      UI->>API: GET /api/jobs/:id
      API->>DB: SELECT job
      API-->>UI: job state
      UI->>API: GET /api/jobs/:id/events?after=n
      API->>DB: SELECT events > n
      API-->>UI: event list
    end

    WK->>DB: claim queued job
    WK->>DB: UPDATE status=running + INSERT event
    WK->>PL: run generation pipeline
    PL-->>WK: result path OR error
    WK->>DB: UPDATE status + INSERT terminal event

    UI->>API: POST /api/jobs/:id/cancel
    API->>DB: set cancel_requested=true
    WK->>DB: observes cancel and marks cancelled
```

## Data Model (Current Core)

```mermaid
erDiagram
    projects ||--o{ generation_jobs : contains
    generation_jobs ||--o{ generation_events : has
    generation_jobs ||--o{ scripts : produces
    generation_jobs ||--o{ artifacts : produces

    projects {
      int id PK
      string name
      datetime created_at
    }

    generation_jobs {
      string id PK
      int project_id FK
      string status
      json payload
      boolean cancel_requested
      int attempt_count
      int max_attempts
      string result_path
      text error_message
      datetime created_at
      datetime started_at
      datetime completed_at
      datetime updated_at
    }

    generation_events {
      int id PK
      string job_id FK
      string event_type
      string level
      text message
      json payload
      datetime created_at
    }

    scripts {
      int id PK
      string job_id FK
      string model_name
      text content
      datetime created_at
    }

    artifacts {
      int id PK
      string job_id FK
      string artifact_type
      string path
      json metadata_json
      datetime created_at
    }
```

## Current Guarantees

- API is fast and non-blocking for generation requests.
- Job state and logs survive API/worker restarts.
- Cancellation is job-scoped (`cancel_requested`) and checked during processing.
- Frontend can recover progress after refresh by polling persisted events.

## Planned Next Hardening

- Add migration tool (Alembic) for schema versioning.
- Add retries/backoff with `next_retry_at` and dead-letter semantics.
- Add artifact metadata population and checksum tracking.
- Add worker concurrency controls and queue metrics endpoints.
