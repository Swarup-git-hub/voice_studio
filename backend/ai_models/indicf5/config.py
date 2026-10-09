from __future__ import annotations

import os
from pathlib import Path


INDICF5_ROOT = Path(__file__).resolve().parent
AI_MODELS_ROOT = INDICF5_ROOT.parent
BACKEND_ROOT = AI_MODELS_ROOT.parent
PROJECT_ROOT = BACKEND_ROOT.parent

VOICES_DIRECTORY = (
    BACKEND_ROOT
    / "app"
    / "voices"
).resolve()

OUTPUT_DIRECTORY = (
    INDICF5_ROOT
    / "server_outputs"
).resolve()

OUTPUT_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)

MODEL_ID = os.getenv(
    "INDICF5_MODEL_ID",
    "ai4bharat/IndicF5",
)

DEVICE = os.getenv(
    "INDICF5_DEVICE",
    "cuda:0",
)

HOST = os.getenv(
    "INDICF5_HOST",
    "127.0.0.1",
)

PORT = int(
    os.getenv(
        "INDICF5_PORT",
        "8002",
    )
)

SAMPLE_RATE = 24000

MAX_TEXT_CHARACTERS = 1500
MAX_TRANSCRIPT_CHARACTERS = 5000

SERVICE_NAME = "IndicF5 GPU Service"
SERVICE_VERSION = "0.1.0"
