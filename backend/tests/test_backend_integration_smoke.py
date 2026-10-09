import inspect

from app.api.speech import router
from app.database.connection import SessionLocal
from app.database.models import GeneratedAudio
from app.database.schemas import GenerateSpeechRequest
from app.main import app
from app.services.engine_router import engine_router
from app.services.tts_service import tts_service


legacy_request = GenerateSpeechRequest(
    voice_id=10,
    text="Legacy compatibility test.",
    speed=1.0,
    volume=1.0,
    bass=0.0,
)

explicit_request = GenerateSpeechRequest(
    voice_id=10,
    text="Explicit IndicF5 test.",
    engine="indicf5",
    allow_fallback=False,
)

service_signature = inspect.signature(
    tts_service.generate_speech
)

database = SessionLocal()

try:
    history_count = (
        database.query(GeneratedAudio).count()
    )
finally:
    database.close()

checks = {
    "Legacy engine default": (
        legacy_request.engine == "auto"
    ),
    "Legacy fallback default": (
        legacy_request.allow_fallback is True
    ),
    "Explicit engine accepted": (
        explicit_request.engine == "indicf5"
    ),
    "Explicit fallback accepted": (
        explicit_request.allow_fallback is False
    ),
    "requested_engine parameter": (
        "requested_engine"
        in service_signature.parameters
    ),
    "allow_fallback parameter": (
        "allow_fallback"
        in service_signature.parameters
    ),
    "Router engines": (
        engine_router.ALLOWED_ENGINES
        == {
            "auto",
            "cosyvoice",
            "indicf5",
        }
    ),
}

print("=" * 80)
print("BACKEND INTEGRATION SMOKE TEST")
print("=" * 80)

print("Application:", app.title)
print("Speech prefix:", router.prefix)
print("TTS service:", type(tts_service).__name__)
print("Router:", type(engine_router).__name__)
print("Service signature:", service_signature)
print("History count:", history_count)

failed = []

for name, passed in checks.items():
    print(
        f"{name}:",
        "PASSED" if passed else "FAILED",
    )

    if not passed:
        failed.append(name)

if failed:
    raise RuntimeError(
        "Smoke checks failed: "
        + ", ".join(failed)
    )

print("=" * 80)
print("BACKEND INTEGRATION SMOKE TEST: PASSED")
print("=" * 80)
