from __future__ import annotations

import json
import wave
from pathlib import Path
from typing import Any

import requests

from app.core.config import settings
from app.database.connection import SessionLocal
from app.database.models import GeneratedAudio


BASE_URL = "http://127.0.0.1:8000"
VOICE_ID = 10

TEST_TEXT = (
    "అందరికీ నమస్కారం. "
    "ఇది పూర్తి HTTP API ఇంటిగ్రేషన్ పరీక్ష."
)


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise RuntimeError(message)


def display_json(
    value: Any,
) -> None:
    print(
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )


database = SessionLocal()

history_before: int | None = None
generation_id: int | None = None
output_path: Path | None = None
response_data: dict[str, Any] | None = None

try:
    output_folder = Path(
        settings.OUTPUT_FOLDER
    ).resolve()

    output_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_files_before = {
        file.name
        for file in output_folder.iterdir()
        if file.is_file()
    }

    history_before = (
        database.query(GeneratedAudio).count()
    )

    payload = {
        "voice_id": VOICE_ID,
        "text": TEST_TEXT,
        "speed": 1.0,
        "volume": 1.0,
        "bass": 0.0,
        "engine": "indicf5",
        "allow_fallback": False,
    }

    print("=" * 80)
    print("SPEECH HTTP INDICF5 ACCEPTANCE TEST")
    print("=" * 80)

    print("Endpoint:", f"{BASE_URL}/speech/generate")
    print("History before:", history_before)

    print("\nREQUEST")
    print("-" * 80)
    display_json(payload)

    response = requests.post(
        f"{BASE_URL}/speech/generate",
        json=payload,
        timeout=(10, 900),
    )

    print("\nHTTP RESPONSE")
    print("-" * 80)
    print("Status code:", response.status_code)

    try:
        parsed_response = response.json()
    except ValueError:
        parsed_response = {
            "raw_body": response.text,
        }

    display_json(parsed_response)

    require(
        response.status_code == 200,
        (
            "POST /speech/generate failed. "
            f"Status={response.status_code}; "
            f"Body={response.text}"
        ),
    )

    require(
        isinstance(parsed_response, dict),
        "The API response is not a JSON object.",
    )

    response_data = parsed_response

    required_fields = {
        "id",
        "voice_id",
        "voice_name",
        "text",
        "output_filename",
        "speed",
        "volume",
        "bass",
        "created_at",
        "engine_requested",
        "engine_used",
        "detected_language",
        "fallback_used",
        "routing_reason",
    }

    missing_fields = sorted(
        required_fields
        - set(response_data)
    )

    require(
        not missing_fields,
        (
            "API response fields are missing: "
            + ", ".join(missing_fields)
        ),
    )

    generation_id = int(
        response_data["id"]
    )

    output_path = (
        output_folder
        / str(response_data["output_filename"])
    ).resolve()

    require(
        output_path.parent == output_folder,
        "Output resolved outside the configured folder.",
    )

    require(
        output_path.exists(),
        f"Generated WAV is missing: {output_path}",
    )

    require(
        output_path.stat().st_size > 0,
        "Generated WAV is empty.",
    )

    with wave.open(
        str(output_path),
        "rb",
    ) as wav_file:
        channels = wav_file.getnchannels()
        sample_rate = wav_file.getframerate()
        sample_width = wav_file.getsampwidth()
        frame_count = wav_file.getnframes()

    duration_seconds = (
        frame_count / sample_rate
    )

    database.expire_all()

    history_after = (
        database.query(GeneratedAudio).count()
    )

    saved_row = (
        database.query(GeneratedAudio)
        .filter(
            GeneratedAudio.id
            == generation_id
        )
        .first()
    )

    print("\nOUTPUT VALIDATION")
    print("-" * 80)
    print("Generation ID:", generation_id)
    print("Output:", output_path)
    print("Output size:", output_path.stat().st_size)
    print("Channels:", channels)
    print("Sample rate:", sample_rate)
    print("Sample width:", sample_width)
    print("Frames:", frame_count)
    print(
        "Duration seconds:",
        round(duration_seconds, 3),
    )
    print("History after:", history_after)

    checks = {
        "Status success": (
            response_data.get("status")
            == "success"
        ),
        "Correct voice": (
            response_data["voice_id"]
            == VOICE_ID
        ),
        "Explicit IndicF5 requested": (
            response_data["engine_requested"]
            == "indicf5"
        ),
        "IndicF5 used": (
            response_data["engine_used"]
            == "indicf5"
        ),
        "Mixed language detected": (
            response_data["detected_language"]
            == "mixed"
        ),
        "No fallback": (
            response_data["fallback_used"]
            is False
        ),
        "Explicit routing reason": (
            response_data["routing_reason"]
            == "explicit_indicf5"
        ),
        "Exactly one history row added": (
            history_after
            == history_before + 1
        ),
        "Response history row exists": (
            saved_row is not None
        ),
        "Mono audio": channels == 1,
        "24 kHz audio": sample_rate == 24000,
        "16-bit PCM audio": sample_width == 2,
        "Audio contains frames": frame_count > 0,
        "Positive duration": duration_seconds > 0,
    }

    print("\nACCEPTANCE CHECKS")
    print("-" * 80)

    failed_checks: list[str] = []

    for check_name, passed in checks.items():
        print(
            f"{check_name}:",
            "PASSED" if passed else "FAILED",
        )

        if not passed:
            failed_checks.append(
                check_name
            )

    if failed_checks:
        raise RuntimeError(
            "HTTP checks failed: "
            + ", ".join(failed_checks)
        )

    print("\n" + "=" * 80)
    print("SPEECH HTTP INDICF5 GENERATION: PASSED")
    print("=" * 80)

finally:
    cleanup_errors: list[str] = []

    try:
        database.rollback()

        test_rows = (
            database.query(GeneratedAudio)
            .filter(
                GeneratedAudio.text
                == TEST_TEXT
            )
            .all()
        )

        cleanup_filenames = {
            row.output_filename
            for row in test_rows
            if row.output_filename
        }

        for row in test_rows:
            database.delete(row)

        database.commit()

    except Exception as error:
        database.rollback()
        cleanup_filenames = set()

        cleanup_errors.append(
            "Database cleanup failed: "
            f"{type(error).__name__}: {error}"
        )

    try:
        if (
            response_data is not None
            and response_data.get(
                "output_filename"
            )
        ):
            cleanup_filenames.add(
                str(
                    response_data[
                        "output_filename"
                    ]
                )
            )

        for filename in cleanup_filenames:
            candidate = (
                Path(settings.OUTPUT_FOLDER)
                / filename
            ).resolve()

            if (
                candidate.parent
                == Path(
                    settings.OUTPUT_FOLDER
                ).resolve()
                and candidate.exists()
            ):
                candidate.unlink()

    except Exception as error:
        cleanup_errors.append(
            "Output cleanup failed: "
            f"{type(error).__name__}: {error}"
        )

    database.expire_all()

    history_final = (
        database.query(GeneratedAudio).count()
    )

    output_files_after = {
        file.name
        for file in Path(
            settings.OUTPUT_FOLDER
        ).resolve().iterdir()
        if file.is_file()
    }

    unexpected_files = (
        output_files_after
        - output_files_before
    )

    print("\nCLEANUP")
    print("-" * 80)
    print("History final:", history_final)
    print(
        "Unexpected new output files:",
        sorted(unexpected_files),
    )

    if (
        history_before is not None
        and history_final != history_before
    ):
        cleanup_errors.append(
            "History count was not restored. "
            f"Before={history_before}, "
            f"Final={history_final}."
        )

    if unexpected_files:
        cleanup_errors.append(
            "Unexpected output files remain: "
            + ", ".join(
                sorted(unexpected_files)
            )
        )

    database.close()

    if cleanup_errors:
        raise RuntimeError(
            " | ".join(cleanup_errors)
        )

    print("HTTP test cleanup: PASSED")

print("\n" + "=" * 80)
print("SPEECH HTTP INDICF5 ACCEPTANCE TEST: PASSED")
print("=" * 80)

