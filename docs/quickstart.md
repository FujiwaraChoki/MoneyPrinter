# Quickstart

Run MoneyPrinter locally with an Ollama model.

## 1) Clone repository

```bash
git clone https://github.com/FujiwaraChoki/MoneyPrinter.git
cd MoneyPrinter
```

## 2) Quick setup (recommended)

Run the interactive setup script:

```bash
./setup.sh
```

This script checks dependencies, sets up `.env`, installs Python packages with `uv`, and can optionally pull an Ollama model.

## 3) Manual setup

Use this path if you prefer to run each step yourself.

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- FFmpeg
- ImageMagick
- Ollama

### Install and create env file

```bash
uv sync
cp .env.example .env
```

Windows PowerShell for `.env` copy:

```powershell
Copy-Item .env.example .env
```

## 4) Configure environment

Set required values in `.env`:

- `TIKTOK_SESSION_ID`
- `PEXELS_API_KEY`

See [Configuration](configuration.md) for all variables.

## Optional: Run tests

```bash
uv sync --group dev
uv run pytest
```

## 5) Start Ollama and pull a model

```bash
ollama serve
ollama pull llama3.1:8b
```

If Ollama runs on another machine/port, set `OLLAMA_BASE_URL` in `.env`.

## 6) Run backend

```bash
uv run python Backend/main.py
```

## 7) Run worker

In a new terminal:

```bash
uv run python Backend/worker.py
```

## 8) Run frontend

In a new terminal:

```bash
cd Frontend
python3 -m http.server 3000
```

Open `http://localhost:3000`.

## 9) Generate video

1. Enter a video subject.
2. Expand advanced options.
3. Choose an Ollama model from the dropdown (loaded dynamically from Ollama).
4. Click Generate.

Output file: `output.mp4` at project root.
