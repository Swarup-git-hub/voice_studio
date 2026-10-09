# AI Voice Studio

AI Voice Studio is a local full-stack voice cloning and text-to-speech workspace. It combines a FastAPI backend, a React/Vite frontend, voice library management, generated-audio history, and routing across CosyVoice and IndicF5 speech engines for English, Telugu, and mixed-language text.

## Features

- Upload and manage reference voices.
- Generate speech from text with speed, volume, bass, and style controls.
- Route generation automatically between CosyVoice and IndicF5.
- Store generated-audio history with playback, download, and delete endpoints.
- Run locally with PowerShell helper scripts or separate backend/frontend commands.

## Project Structure

```text
backend/
  app/                  FastAPI application, database models, APIs, services
  ai_models/            Local model integration code and runtime checkouts
  scripts/              Database/bootstrap utilities
  tests/                Integration and milestone verification tests
frontend/
  src/                  React application
  public/               Static frontend assets
docs/                   Project documentation
start_ai_voice_studio.ps1
stop_ai_voice_studio.ps1
```

## Repository Hygiene

This repository intentionally excludes local runtime artifacts:

- Python virtual environments (`.venv`, `indicf5_env`, `cosyvoice_env`)
- Node dependencies and frontend build output
- `.env` files
- SQLite databases
- uploaded reference voices
- generated audio
- logs, milestone reports, caches, backups, and downloaded pretrained weights
- the nested CosyVoice checkout under `backend/ai_models/cosyvoice`

Use `.env.example` as the safe template for local configuration.

## Prerequisites

- Windows PowerShell
- Python 3.10 or newer
- Node.js and npm
- FFmpeg available on `PATH`
- Model/runtime dependencies required by CosyVoice and IndicF5
- CosyVoice cloned locally into `backend/ai_models/cosyvoice`

## Setup

1. Create a local environment file:

```powershell
Copy-Item backend\.env.example backend\.env
```

2. Create and activate a Python environment for the backend:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

3. Install frontend dependencies:

```powershell
cd frontend
npm install
cd ..
```

4. Start the app with the helper script:

```powershell
.\start_ai_voice_studio.ps1
```

The frontend runs at `http://127.0.0.1:5173`, and the backend runs at `http://127.0.0.1:8000`.

To stop local services:

```powershell
.\stop_ai_voice_studio.ps1
```

## Manual Development

Backend:

```powershell
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend:

```powershell
cd frontend
npm run dev
```

The Vite dev server proxies `/api/*` requests to the FastAPI backend.

## API Overview

- `GET /health` - backend health check
- `POST /voice/upload` - upload a reference voice
- `GET /voice/list` - list saved voices
- `POST /speech/generate` - generate speech
- `GET /speech/history` - list generated audio history
- `GET /speech/history/{id}/audio` - stream generated audio
- `GET /speech/history/{id}/download` - download generated audio

## Safety Notes

Only use voices and datasets you have the right to process. See `VOICE_USE_POLICY.md`, `PRIVACY_AND_RETENTION.md`, `SECURITY.md`, `LICENSING.md`, and `MODEL_AND_DATA_TERMS.md` for project policy and release notes.

## License

See `LICENSE`, `NOTICE`, and `THIRD_PARTY_NOTICES.md`.
