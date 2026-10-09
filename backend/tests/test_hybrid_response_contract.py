from __future__ import annotations

from datetime import datetime
from typing import get_args

from app.database.schemas import (
    GenerateSpeechResponse,
)


checks_passed = 0


def check(
    name: str,
    condition: bool,
    detail: str = "",
) -> None:
    global checks_passed

    if not condition:
        message = f"{name}: FAILED"

        if detail:
            message += f"\n{detail}"

        raise AssertionError(message)

    checks_passed += 1
    print(f"{name}: PASSED")


print("=" * 80)
print(
    "MILESTONE 10.6.7D HYBRID RESPONSE CONTRACT"
)
print("=" * 80)

engine_field = (
    GenerateSpeechResponse
    .model_fields["engine_used"]
)

allowed_engines = set(
    get_args(
        engine_field.annotation
    )
)

check(
    "CosyVoice remains allowed",
    "cosyvoice" in allowed_engines,
    repr(allowed_engines),
)

check(
    "IndicF5 remains allowed",
    "indicf5" in allowed_engines,
    repr(allowed_engines),
)

check(
    "Hybrid engine is allowed",
    "hybrid" in allowed_engines,
    repr(allowed_engines),
)

response = GenerateSpeechResponse(
    id=9999,
    voice_id=10,
    voice_name="Contract Test Voice",
    text=(
        "The backend receives a request. "
        "ఇప్పుడు తెలుగు భాగం ప్రారంభమవుతుంది."
    ),
    output_filename=(
        "hybrid_contract.wav"
    ),
    speed=1.0,
    volume=1.0,
    bass=0.0,
    created_at=datetime.now(),
    audio_url=(
        "/speech/history/9999/audio"
    ),
    download_url=(
        "/speech/history/9999/download"
    ),
    engine_requested="auto",
    engine_used="hybrid",
    detected_language="mixed",
    fallback_used=False,
    routing_reason=(
        "segmented_phrase_routing:"
        "2_segments:cosyvoice,indicf5"
    ),
    quality_warning=None,
)

check(
    "Hybrid response validates successfully",
    response.engine_used == "hybrid",
)

check(
    "Mixed-language metadata is preserved",
    response.detected_language == "mixed",
)

check(
    "Auto request metadata is preserved",
    response.engine_requested == "auto",
)

print()
print("=" * 80)
print(
    "MILESTONE 10.6.7D HYBRID RESPONSE "
    "CONTRACT: PASSED"
)
print("=" * 80)
print("Checks passed:", checks_passed)
