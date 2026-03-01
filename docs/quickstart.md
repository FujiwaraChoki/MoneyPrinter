# Quickstart

Run MoneyPrinter locally with an Ollama model.

## 1) Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- FFmpeg
- ImageMagick
- Ollama

## 2) Clone and install

```bash
git clone https://github.com/FujiwaraChoki/MoneyPrinter.git
cd MoneyPrinter
uv sync
cp .env.example .env
```

Windows PowerShell for `.env` copy:

```powershell
Copy-Item .env.example .env
```

## 3) Configure environment

Set required values in `.env`:

- `TIKTOK_SESSION_ID`
- `PEXELS_API_KEY`

See [Configuration](configuration.md) for all variables.

## 4) Start Ollama and pull a model

```bash
ollama serve
ollama pull llama3.1:8b
```

If Ollama runs on another machine/port, set `OLLAMA_BASE_URL` in `.env`.

## 5) Run backend

```bash
uv run python Backend/main.py
```

## 6) Run frontend

In a new terminal:

```bash
cd Frontend
python3 -m http.server 3000
```

Open `http://localhost:3000`.

## 7) Generate video

1. Enter a video subject.
2. Expand advanced options.
3. Choose an Ollama model from the dropdown (loaded dynamically from Ollama).
4. Click Generate.

Output file: `output.mp4` at project root.
