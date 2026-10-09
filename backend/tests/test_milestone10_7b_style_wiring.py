from __future__ import annotations

import inspect
import sqlite3
from pathlib import Path

from pydantic import ValidationError

from app.database.models import GeneratedAudio
from app.database.schemas import (
    GenerateSpeechRequest,
    GenerateSpeechResponse,
    GeneratedAudioResponse,
    VoiceStyle,
)
from app.services.tts_service import TTSService


BACKEND_ROOT = Path(__file__).resolve().parents[1]

DATABASE_PATH = (
    BACKEND_ROOT
    / "voice.db"
)

SPEECH_PATH = (
    BACKEND_ROOT
    / "app"
    / "api"
    / "speech.py"
)

TTS_PATH = (
    BACKEND_ROOT
    / "app"
    / "services"
    / "tts_service.py"
)


EXPECTED_STYLES = {
    "neutral",
    "professional",
    "energetic",
    "calm",
    "storytelling",
}


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


print("=" * 92)
print(
    "MILESTONE 10.7B — STYLE API, "
    "DATABASE AND SERVICE CONTRACT"
)
print("=" * 92)

voice_style_values = set(
    VoiceStyle.__args__
)

check(
    "VoiceStyle contains the five locked styles",
    voice_style_values == EXPECTED_STYLES,
    repr(voice_style_values),
)

default_request = GenerateSpeechRequest(
    voice_id=10,
    text="Style contract test.",
)

check(
    "Omitted request style defaults to neutral",
    default_request.style == "neutral",
)

for style in sorted(EXPECTED_STYLES):
    request = GenerateSpeechRequest(
        voice_id=10,
        text="Style contract test.",
        style=style,
    )

    check(
        f"Request accepts {style}",
        request.style == style,
    )

invalid_style_rejected = False

try:
    GenerateSpeechRequest(
        voice_id=10,
        text="Invalid style contract test.",
        style="angry",
    )
except ValidationError:
    invalid_style_rejected = True

check(
    "Invalid request style is rejected",
    invalid_style_rejected,
)

check(
    "Request schema exposes style",
    "style"
    in GenerateSpeechRequest.model_fields,
)

check(
    "History schema exposes style",
    "style"
    in GeneratedAudioResponse.model_fields,
)

check(
    "Generation schema inherits style",
    "style"
    in GenerateSpeechResponse.model_fields,
)

style_column = (
    GeneratedAudio
    .__table__
    .columns
    .get("style")
)

check(
    "GeneratedAudio model exposes style",
    style_column is not None,
)

check(
    "GeneratedAudio style is non-nullable",
    (
        style_column is not None
        and style_column.nullable is False
    ),
)

check(
    "GeneratedAudio style default is neutral",
    (
        style_column is not None
        and style_column.default is not None
        and style_column.default.arg
        == "neutral"
    ),
)

connection = sqlite3.connect(
    DATABASE_PATH
)

try:
    table_info = connection.execute(
        "PRAGMA table_info(generated_audio)"
    ).fetchall()

    column_map = {
        column[1]: column
        for column in table_info
    }

    check(
        "Database contains the style column",
        "style" in column_map,
        repr(column_map),
    )

    style_info = column_map["style"]

    check(
        "Database style column is non-null",
        int(style_info[3]) == 1,
        repr(style_info),
    )

    normalised_default = (
        str(style_info[4])
        .strip()
        .strip("'")
        .strip('"')
    )

    check(
        "Database style default is neutral",
        normalised_default == "neutral",
        repr(style_info[4]),
    )

    invalid_rows = connection.execute(
        """
        SELECT COUNT(*)
        FROM generated_audio
        WHERE style IS NULL
           OR TRIM(style) = ''
        """
    ).fetchone()[0]

    check(
        "No history row has an empty style",
        invalid_rows == 0,
        f"Invalid rows={invalid_rows}",
    )

    distinct_styles = {
        row[0]
        for row in connection.execute(
            """
            SELECT DISTINCT style
            FROM generated_audio
            """
        ).fetchall()
    }

    check(
        "Legacy rows were migrated to neutral",
        distinct_styles <= {
            "neutral"
        },
        repr(distinct_styles),
    )

finally:
    connection.close()

speech_source = SPEECH_PATH.read_text(
    encoding="utf-8-sig"
)

tts_source = TTS_PATH.read_text(
    encoding="utf-8-sig"
)

check(
    "Speech API passes request.style",
    "style=request.style"
    in speech_source,
)

check(
    "History serialisation returns style",
    '"style": generation.style'
    in speech_source,
)

tts_signature = inspect.signature(
    TTSService.generate_speech
)

check(
    "TTS service accepts style",
    "style"
    in tts_signature.parameters,
)

check(
    "TTS style defaults to neutral",
    (
        tts_signature
        .parameters["style"]
        .default
        == "neutral"
    ),
)

check(
    "TTS service contains the locked styles",
    TTSService.ALLOWED_STYLES
    == EXPECTED_STYLES,
    repr(
        TTSService.ALLOWED_STYLES
    ),
)

check(
    "TTS service persists resolved style",
    "style=clean_style"
    in tts_source,
)

check(
    "TTS result exposes resolved style",
    '"style": clean_style'
    in tts_source,
)

print()
print("=" * 92)
print(
    "MILESTONE 10.7B STYLE WIRING "
    "CONTRACT: PASSED"
)
print("=" * 92)
print("Checks passed:", checks_passed)
