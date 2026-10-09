import torch
from pathlib import Path

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

BASE_DIR = Path(__file__).resolve().parent.parent

VOICE_FOLDER = BASE_DIR / "voices"

OUTPUT_FOLDER = BASE_DIR / "outputs"

OUTPUT_FOLDER.mkdir(exist_ok=True)

DEFAULT_SAMPLE_RATE = 24000

SUPPORTED_LANGUAGES = [
    "English",
    "Telugu",
    "Mixed",
]

DEFAULT_SPEED = 1.0
