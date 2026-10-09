from __future__ import annotations

import io
import wave
from contextlib import redirect_stdout
from pathlib import Path

from app.core.config import settings
from app.database.connection import SessionLocal
from app.database.models import GeneratedAudio
from app.services.tts_service import tts_service


VOICE_ID = 10
REQUESTED_SPEED = 1.25

database = SessionLocal()

history_before: int | None = None
generation_id: int | None = None
output_path: Path | None = None
output_files_before: set[str] = set()


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise RuntimeError(message)


try:
    output_folder = Path(
        settings.OUTPUT_FOLDER
    ).resolve()

    output_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_files_before = {
        path.name
        for path in output_folder.iterdir()
        if path.is_file()
    }

    history_before = (
        database.query(GeneratedAudio).count()
    )

    print("=" * 80)
    print("INTEGRATED INDICF5 TRANSACTION TEST")
    print("=" * 80)

    print("Voice ID:", VOICE_ID)
    print("Requested engine: indicf5")
    print("Requested speed:", REQUESTED_SPEED)
    print("History before:", history_before)

    log_capture = io.StringIO()

    with redirect_stdout(log_capture):
        result = tts_service.generate_speech(
            db=database,
            voice_id=VOICE_ID,
            text=(
                "అందరికీ నమస్కారం. "
                "ఇది పూర్తి బ్యాకెండ్ ఇంటిగ్రేషన్ పరీక్ష."
            ),
            speed=REQUESTED_SPEED,
            volume=1.0,
            bass=0.0,
            requested_engine="indicf5",
            allow_fallback=False,
        )

    service_logs = log_capture.getvalue()

    print("\nTTS SERVICE LOG")
    print("-" * 80)
    print(service_logs)

    generation_id = result["id"]

    output_path = (
        output_folder
        / result["output_filename"]
    ).resolve()

    require(
        output_path.exists(),
        "Final integrated WAV was not created.",
    )

    require(
        output_path.is_file(),
        "Final integrated output is not a file.",
    )

    require(
        output_path.stat().st_size > 0,
        "Final integrated WAV is empty.",
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

    history_after_generation = (
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

    print("\nGENERATION RESULT")
    print("-" * 80)

    print("Generation ID:", generation_id)
    print(
        "Engine requested:",
        result["engine_requested"],
    )
    print(
        "Engine used:",
        result["engine_used"],
    )
    print(
        "Detected language:",
        result["detected_language"],
    )
    print(
        "Fallback used:",
        result["fallback_used"],
    )
    print(
        "Routing reason:",
        result["routing_reason"],
    )
    print("Requested speed:", result["speed"])
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
    print(
        "History after generation:",
        history_after_generation,
    )

    checks = {
        "Explicit IndicF5 requested": (
            result["engine_requested"]
            == "indicf5"
        ),
        "IndicF5 used": (
            result["engine_used"]
            == "indicf5"
        ),
        "No fallback": (
            result["fallback_used"]
            is False
        ),
        "Explicit routing reason": (
            result["routing_reason"]
            == "explicit_indicf5"
        ),
        "Speed returned correctly": (
            abs(
                float(result["speed"])
                - REQUESTED_SPEED
            )
            < 0.0001
        ),
        "FFmpeg speed enabled": (
            "Apply speed in FFmpeg: True"
            in service_logs
        ),
        "FFmpeg atempo applied": (
            "atempo=1.2500"
            in service_logs
        ),
        "CosyVoice reference skipped": (
            "CosyVoice reference preparation "
            "not required."
            in service_logs
        ),
        "History row added": (
            history_after_generation
            == history_before + 1
        ),
        "Saved row exists": (
            saved_row is not None
        ),
        "Saved speed correct": (
            saved_row is not None
            and abs(
                float(saved_row.speed)
                - REQUESTED_SPEED
            )
            < 0.0001
        ),
        "Mono audio": channels == 1,
        "24 kHz audio": (
            sample_rate == 24000
        ),
        "16-bit PCM": (
            sample_width == 2
        ),
        "Audio contains frames": (
            frame_count > 0
        ),
        "Positive duration": (
            duration_seconds > 0
        ),
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
            "Integrated transaction checks failed: "
            + ", ".join(failed_checks)
        )

    print("\n" + "=" * 80)
    print("INTEGRATED INDICF5 GENERATION: PASSED")
    print("=" * 80)

finally:
    cleanup_errors: list[str] = []

    try:
        database.rollback()

        if generation_id is not None:
            generation = (
                database.query(GeneratedAudio)
                .filter(
                    GeneratedAudio.id
                    == generation_id
                )
                .first()
            )

            if generation is not None:
                database.delete(generation)
                database.commit()

    except Exception as error:
        database.rollback()

        cleanup_errors.append(
            "Database cleanup failed: "
            f"{type(error).__name__}: {error}"
        )

    try:
        if (
            output_path is not None
            and output_path.exists()
        ):
            output_path.unlink()

    except Exception as error:
        cleanup_errors.append(
            "Output cleanup failed: "
            f"{type(error).__name__}: {error}"
        )

    history_final = (
        database.query(GeneratedAudio).count()
    )

    output_files_after = {
        path.name
        for path in Path(
            settings.OUTPUT_FOLDER
        ).resolve().iterdir()
        if path.is_file()
    }

    new_output_files = (
        output_files_after
        - output_files_before
    )

    print("\nCLEANUP")
    print("-" * 80)
    print(
        "Generation ID removed:",
        generation_id,
    )
    print(
        "Output removed:",
        output_path,
    )
    print(
        "History final:",
        history_final,
    )
    print(
        "Unexpected new output files:",
        sorted(new_output_files),
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

    if new_output_files:
        cleanup_errors.append(
            "Unexpected output files remain: "
            + ", ".join(
                sorted(new_output_files)
            )
        )

    database.close()

    if cleanup_errors:
        raise RuntimeError(
            " | ".join(cleanup_errors)
        )

    print("Transaction cleanup: PASSED")

print("\n" + "=" * 80)
print("INTEGRATED INDICF5 TRANSACTION TEST: PASSED")
print("=" * 80)
