from pathlib import Path
import wave

from app.core.config import settings
from app.database.connection import SessionLocal
from app.database.models import GeneratedAudio
from app.database.models import Voice
from app.services.engine_router import engine_router


VOICE_ID = 10
OUTPUT_FILENAME = (
    "milestone10_4_router_telugu_test.wav"
)


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise RuntimeError(message)


database = SessionLocal()

try:
    history_before = (
        database.query(GeneratedAudio).count()
    )

    voice = (
        database.query(Voice)
        .filter(Voice.id == VOICE_ID)
        .first()
    )

    require(
        voice is not None,
        f"Voice ID {VOICE_ID} was not found.",
    )

    require(
        bool(voice.wav_filename),
        f"Voice ID {VOICE_ID} has no reference WAV.",
    )

    require(
        bool(voice.transcript),
        f"Voice ID {VOICE_ID} has no transcript.",
    )

    original_reference = (
        Path(settings.VOICE_FOLDER)
        / voice.wav_filename
    ).resolve()

    output_path = (
        Path(settings.OUTPUT_FOLDER)
        / OUTPUT_FILENAME
    ).resolve()

    require(
        original_reference.exists(),
        (
            "Reference WAV was not found: "
            f"{original_reference}"
        ),
    )

    require(
        original_reference.is_file(),
        "Reference WAV path is not a file.",
    )

    output_path.unlink(
        missing_ok=True
    )

    target_text = (
        "అందరికీ నమస్కారం. "
        "ఇది ఆటోమేటిక్ ఇంజిన్ రూటర్ పరీక్ష."
    )

    detected_before = (
        engine_router.detect_language(
            target_text
        )
    )

    print("=" * 80)
    print("LIVE AUTO-TELUGU ROUTER TEST")
    print("=" * 80)

    print("Voice ID:", voice.id)
    print("Voice name:", voice.voice_name)
    print("Reference:", original_reference)
    print("Reference exists:", original_reference.exists())
    print("Target text:", repr(target_text))
    print(
        "Detected before generation:",
        detected_before,
    )
    print("History before:", history_before)

    require(
        detected_before == "telugu",
        (
            "Language detection failed before "
            f"generation: {detected_before}"
        ),
    )

    result = engine_router.generate(
        requested_engine="auto",
        allow_fallback=True,
        original_reference_audio=str(
            original_reference
        ),
        # CosyVoice is not expected to run because this is
        # Telugu-primary routing. This argument remains required
        # by the common router contract.
        cosyvoice_reference_audio=str(
            original_reference
        ),
        prompt_text=voice.transcript,
        text=target_text,
        output_path=str(output_path),
        speed=1.0,
    )

    require(
        output_path.exists(),
        "Router output was not created.",
    )

    require(
        output_path.stat().st_size > 0,
        "Router output is empty.",
    )

    with wave.open(
        str(output_path),
        "rb",
    ) as wav_file:
        channels = wav_file.getnchannels()
        sample_rate = wav_file.getframerate()
        sample_width = wav_file.getsampwidth()
        frame_count = wav_file.getnframes()

    history_after = (
        database.query(GeneratedAudio).count()
    )

    print("\nROUTING RESULT")
    print("-" * 80)
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
    print(
        "Quality warning:",
        result["quality_warning"],
    )
    print(
        "Failed attempts:",
        result["failed_attempts"],
    )
    print(
        "Speed applied by engine:",
        result["speed_applied_by_engine"],
    )

    print("\nOUTPUT VALIDATION")
    print("-" * 80)
    print("Output:", output_path)
    print("Size:", output_path.stat().st_size)
    print("Channels:", channels)
    print("Sample rate:", sample_rate)
    print("Sample width:", sample_width)
    print("Frames:", frame_count)
    print("History before:", history_before)
    print("History after:", history_after)

    checks = {
        "Telugu detected": (
            result["detected_language"]
            == "telugu"
        ),
        "IndicF5 selected": (
            result["engine_used"]
            == "indicf5"
        ),
        "Auto requested": (
            result["engine_requested"]
            == "auto"
        ),
        "No fallback": (
            result["fallback_used"]
            is False
        ),
        "Correct routing reason": (
            result["routing_reason"]
            == "auto_telugu_indicf5_primary"
        ),
        "No failed attempts": (
            result["failed_attempts"] == []
        ),
        "IndicF5 native speed metadata": (
            result["speed_applied_by_engine"]
            is False
        ),
        "Mono audio": channels == 1,
        "24 kHz audio": sample_rate == 24000,
        "16-bit PCM": sample_width == 2,
        "Audio has frames": frame_count > 0,
        "History unchanged": (
            history_before == history_after
        ),
    }

    print("\nACCEPTANCE CHECKS")
    print("-" * 80)

    failed_checks = []

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
            "Live Auto-Telugu checks failed: "
            + ", ".join(failed_checks)
        )

    print("\n" + "=" * 80)
    print("LIVE AUTO-TELUGU ROUTER: PASSED")
    print("=" * 80)

finally:
    database.close()
