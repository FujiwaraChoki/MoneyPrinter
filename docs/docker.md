# Docker

Run MoneyPrinter frontend, API, worker, and Postgres with Docker Compose.

## 1) Prepare environment

```bash
cp .env.example .env
```

Set required keys in `.env`:

- `TIKTOK_SESSION_ID`
- `PEXELS_API_KEY`

Database defaults (already in `.env.example`):

- `POSTGRES_DB=moneyprinter`
- `POSTGRES_USER=moneyprinter`
- `POSTGRES_PASSWORD=moneyprinter`
- `DATABASE_URL=postgresql+psycopg://moneyprinter:moneyprinter@postgres:5432/moneyprinter`

## 2) Ollama connectivity

By default, Docker backend expects Ollama on host machine:

- `OLLAMA_BASE_URL=http://host.docker.internal:11434`

Linux support is included via compose `extra_hosts` host-gateway mapping.

If Ollama runs in another container or machine, set `OLLAMA_BASE_URL` accordingly.

## 3) Start services

```bash
docker compose up --build
```

## 4) Access apps

- Frontend: `http://localhost:8001`
- Backend API: `http://localhost:8080`
- Postgres: `localhost:5432`

## 5) Verify model listing

```bash
curl http://localhost:8080/api/models
```

You should receive a JSON payload with `models` and `default`.

## 6) Queue a generation job

```bash
curl -X POST http://localhost:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{"videoSubject":"AI business ideas","aiModel":"llama3.1:8b","voice":"en_us_001","paragraphNumber":1,"customPrompt":""}'
```

Response includes `jobId`. Query status and events:

```bash
curl http://localhost:8080/api/jobs/<jobId>
curl "http://localhost:8080/api/jobs/<jobId>/events?after=0"
```
