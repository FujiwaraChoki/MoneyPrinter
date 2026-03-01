# Docker

Run MoneyPrinter frontend and backend with Docker Compose.

## 1) Prepare environment

```bash
cp .env.example .env
```

Set required keys in `.env`:

- `TIKTOK_SESSION_ID`
- `PEXELS_API_KEY`

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

## 5) Verify model listing

```bash
curl http://localhost:8080/api/models
```

You should receive a JSON payload with `models` and `default`.
