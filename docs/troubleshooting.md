# Troubleshooting

## No Ollama models in dropdown

- Ensure Ollama is running: `ollama serve`
- Ensure at least one model exists: `ollama list`
- Pull a model if needed: `ollama pull llama3.1:8b`
- Verify backend can reach Ollama base URL in `.env` (`OLLAMA_BASE_URL`)

## Frontend cannot connect to backend

- Confirm backend is running on port `8080`
- Confirm frontend is opened from local server (for example `python3 -m http.server`)
- Check browser console/network for `/api/generate` or `/api/models` failures

## ImageMagick not detected

- Install ImageMagick and ensure executable is on `PATH`
- Or set explicit path in `.env`, for example:

```env
IMAGEMAGICK_BINARY="/usr/local/bin/magick"
```

Windows example:

```env
IMAGEMAGICK_BINARY="C:\\Program Files\\ImageMagick-7.1.1-Q16-HDRI\\magick.exe"
```

## No stock videos found

- Verify `PEXELS_API_KEY` is valid
- Try a broader video subject
- Retry generation; stock results vary by query

## Subtitles fail

- If using AssemblyAI, verify `ASSEMBLY_AI_API_KEY`
- If not using AssemblyAI, local subtitle generation should still work

## YouTube upload skipped

- Place `client_secret.json` inside `Backend/`
- Enable required YouTube scopes and OAuth consent in Google Cloud
