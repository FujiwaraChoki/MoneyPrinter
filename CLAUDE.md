# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MoneyPrinter automates YouTube Shorts creation from text topics. It uses Ollama for script generation, TikTok TTS for voiceover, Pexels for stock footage, and moviepy/ImageMagick for video composition. Output: a 9:16 vertical video (`output.mp4`).

## Commands

### Setup
```bash
cp .env.example .env        # then fill in API keys
uv sync                     # install dependencies
ollama serve                # start Ollama (separate terminal)
ollama pull llama3.1:8b     # pull default model
```

### Run (local)
```bash
uv run python Backend/main.py                              # backend on :8080
python3 -m http.server 3000 --directory Frontend           # frontend on :3000
```

### Run (Docker)
```bash
docker compose up --build   # frontend :8001, backend :8080
```

### Verify
```bash
uv run python -m compileall Backend          # syntax check
curl http://localhost:8080/api/models         # API smoke test
```

### Tests
No test suite exists yet. If added, use pytest:
```bash
uv run pytest -q                                           # all tests
uv run pytest tests/test_file.py::test_name -q             # single test
```

## Architecture

### Video Generation Pipeline (end-to-end flow)

```
User input (Frontend) → POST /api/generate → Background thread in main.py
  → gpt.py: generate_script() via Ollama
  → gpt.py: get_search_terms() → JSON keywords
  → search.py: Pexels API → download stock clips to temp/
  → tiktokvoice.py: TTS per sentence → MP3 chunks (threaded)
  → video.py: generate_subtitles() → .srt (AssemblyAI or local timestamps)
  → video.py: combine_videos() → concatenate/crop to 9:16
  → video.py: generate_video() → burn subtitles via ImageMagick, merge audio
  → (optional) mix background music from Songs/ at 10% volume
  → (optional) youtube.py: OAuth2 upload
  → output.mp4
```

### Frontend ↔ Backend Communication
- **REST**: JSON payloads to Flask endpoints (`/api/generate`, `/api/cancel`, `/api/models`, `/api/upload-songs`)
- **SSE**: Real-time log streaming via `/api/logs` (logstream.py). Event types: `log`, `complete`, `error`, `cancelled`

### Key Backend Modules
| File | Responsibility |
|------|---------------|
| `main.py` | Flask app, API endpoints, generation orchestration (background thread) |
| `gpt.py` | Ollama client: script generation, search terms, YouTube metadata |
| `video.py` | Video processing: combine clips, burn subtitles, merge audio |
| `search.py` | Pexels stock video search and download |
| `tiktokvoice.py` | TikTok TTS API (60+ voices, 300-char chunking, threaded) |
| `youtube.py` | YouTube upload via Google API with OAuth2 |
| `utils.py` | Path constants, env validation, ImageMagick detection |
| `logstream.py` | Thread-safe SSE log queue |

### Frontend
- `index.html`: UI with inline CSS, form fields, live log viewer
- `app.js`: API client (`apiRequest()`), SSE log stream, localStorage persistence

### Runtime Directories
- `temp/`: intermediate video/audio files (cleared each generation)
- `subtitles/`: generated .srt files (cleared each generation)
- `Songs/`: user-uploaded background music MP3s
- `fonts/`: subtitle font (`bold_font.ttf`)

## Required Environment Variables

- `TIKTOK_SESSION_ID` — TikTok cookie for TTS
- `PEXELS_API_KEY` — stock video API
- `IMAGEMAGICK_BINARY` — leave empty to auto-detect from PATH

Optional: `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `ASSEMBLY_AI_API_KEY`

## Conventions

- **Python**: 4-space indent, `snake_case`, type hints on all new/modified signatures, `pathlib.Path` for filesystem ops
- **JS**: `camelCase`, centralized API calls via `apiRequest()`
- **API responses**: `{"status": "success|error", ...}` with proper HTTP codes
- **Long-running work**: background thread pattern with global `GENERATING` flag, SSE streaming
- **Concurrency**: only one video generation at a time (enforced by `GENERATING` flag)
- Update `docs/` when setup, env vars, or runtime behavior changes
