from __future__ import annotations

import json
import shutil
import wave
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from app.audio.style_profiles import (
    resolve_style_controls,
)
from app.core.config import settings
from app.services.tts_service import (
    tts_service,
)


BACKEND_ROOT = Path(__file__).resolve().parents[1]

BASE_URL = "http://127.0.0.1:8000"
COSYVOICE_URL = "http://127.0.0.1:8001"

VOICE_ID = 10

TEST_TEXT = (
    "This energetic style test verifies that the final "
    "audio pipeline applies a quicker and stronger delivery "
    "after speech synthesis is complete."
)

SOURCE_NEUTRAL = (
    BACKEND_ROOT
    / "milestone_reports"
    / "style_comparisons"
    / "milestone10_7d3_20260725_223438"
    / "neutral.wav"
)

OUTPUT_FOLDER = Path(
    settings.OUTPUT_FOLDER
).expanduser().resolve()

COMPARISON_ROOT = (
    BACKEND_ROOT
    / "milestone_reports"
    / "style_comparisons"
)

comparison_timestamp = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

COMPARISON_FOLDER = (
    COMPARISON_ROOT
    / f"milestone10_7d5b_{comparison_timestamp}"
)

REPORT_PATH = (
    COMPARISON_FOLDER
    / "comparison_report.json"
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

        raise AssertionError(
            message
        )

    checks_passed += 1

    print(
        f"{name}: PASSED"
    )


def response_json(
    response: requests.Response,
) -> Any:
    try:
        return response.json()

    except ValueError as error:
        raise AssertionError(
            "Expected a JSON response.\n"
            f"HTTP status: {response.status_code}\n"
            f"Response: {response.text[:1000]}"
        ) from error


def read_wav_metadata(
    path: Path,
) -> dict[str, float | int]:
    with wave.open(
        str(path),
        "rb",
    ) as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frames = wav_file.getnframes()

    return {
        "channels": channels,
        "sample_width": sample_width,
        "sample_rate": sample_rate,
        "frames": frames,
        "duration_seconds": (
            frames
            / sample_rate
        ),
    }


print("=" * 92)
print(
    "MILESTONE 10.7D-5B — LIVE CORRECTED "
    "STYLE PIPELINE AND SAME-SOURCE COMPARISON"
)
print("=" * 92)

COMPARISON_FOLDER.mkdir(
    parents=True,
    exist_ok=True,
)

generated_id: int | None = None
generated_output_path: Path | None = None
record_deleted = False

pending_before = {
    path.name
    for path in OUTPUT_FOLDER.glob(
        "*.delete_pending"
    )
}

check(
    "Previous Neutral comparison source exists",
    (
        SOURCE_NEUTRAL.exists()
        and SOURCE_NEUTRAL.is_file()
        and SOURCE_NEUTRAL.stat().st_size
        > 44
    ),
    str(
        SOURCE_NEUTRAL
    ),
)

try:
    # ========================================================
    # Live services
    # ========================================================

    backend_health = requests.get(
        f"{BASE_URL}/health",
        timeout=20,
    )

    check(
        "Main backend is healthy",
        backend_health.status_code == 200,
        backend_health.text,
    )

    cosyvoice_health = requests.get(
        f"{COSYVOICE_URL}/health",
        timeout=30,
    )

    check(
        "CosyVoice service is healthy",
        cosyvoice_health.status_code == 200,
        cosyvoice_health.text,
    )

    history_url = (
        f"{BASE_URL}/speech/history"
    )

    history_before_response = requests.get(
        history_url,
        timeout=30,
    )

    history_before = response_json(
        history_before_response
    )

    check(
        "History is readable before generation",
        (
            history_before_response.status_code
            == 200
            and isinstance(
                history_before,
                list,
            )
        ),
        repr(
            history_before
        ),
    )

    history_ids_before = {
        int(
            item["id"]
        )
        for item in history_before
    }

    # ========================================================
    # Live Energetic request
    # ========================================================

    payload = {
        "voice_id": VOICE_ID,
        "text": TEST_TEXT,
        "speed": 1.0,
        "volume": 1.0,
        "bass": 0.0,
        "style": "energetic",
        "engine": "cosyvoice",
        "allow_fallback": False,
    }

    print()
    print("LIVE ENERGETIC REQUEST")
    print("-" * 92)

    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
    )

    generation_response = requests.post(
        f"{BASE_URL}/speech/generate",
        json=payload,
        timeout=600,
    )

    generation = response_json(
        generation_response
    )

    print()
    print(
        json.dumps(
            generation,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )

    check(
        "Energetic generation returned HTTP 200",
        generation_response.status_code
        == 200,
        repr(
            generation
        ),
    )

    required_fields = {
        "id",
        "output_filename",
        "speed",
        "volume",
        "bass",
        "style",
        "engine_requested",
        "engine_used",
        "fallback_used",
        "audio_url",
        "download_url",
    }

    missing_fields = (
        required_fields
        - set(
            generation
        )
    )

    check(
        "Generation response contains required metadata",
        not missing_fields,
        (
            "Missing fields: "
            f"{sorted(missing_fields)}"
        ),
    )

    check(
        "Response stores Energetic style",
        generation["style"]
        == "energetic",
        repr(
            generation["style"]
        ),
    )

    check(
        "Response preserves requested controls",
        (
            float(
                generation["speed"]
            )
            == 1.0
            and float(
                generation["volume"]
            )
            == 1.0
            and float(
                generation["bass"]
            )
            == 0.0
        ),
        repr(
            {
                "speed": generation["speed"],
                "volume": generation["volume"],
                "bass": generation["bass"],
            }
        ),
    )

    check(
        "Request preserves explicit CosyVoice",
        generation["engine_requested"]
        == "cosyvoice",
        repr(
            generation["engine_requested"]
        ),
    )

    check(
        "Live generation used CosyVoice",
        generation["engine_used"]
        == "cosyvoice",
        repr(
            generation["engine_used"]
        ),
    )

    check(
        "Live generation did not use fallback",
        generation["fallback_used"]
        is False,
        repr(
            generation["fallback_used"]
        ),
    )

    generated_id = int(
        generation["id"]
    )

    check(
        "Generation ID is new",
        generated_id
        not in history_ids_before,
        str(
            generated_id
        ),
    )

    generated_output_path = (
        OUTPUT_FOLDER
        / generation[
            "output_filename"
        ]
    ).resolve()

    check(
        "Live generated WAV exists",
        (
            generated_output_path.exists()
            and generated_output_path.is_file()
            and generated_output_path.stat().st_size
            > 44
        ),
        str(
            generated_output_path
        ),
    )

    playback_url = (
        f"{BASE_URL}/speech/history/"
        f"{generated_id}/audio"
    )

    playback_response = requests.get(
        playback_url,
        timeout=60,
    )

    check(
        "Live playback returned HTTP 200",
        playback_response.status_code
        == 200,
        playback_response.text[:500],
    )

    check(
        "Live playback returned audio bytes",
        len(
            playback_response.content
        )
        > 44,
        (
            "Bytes="
            f"{len(playback_response.content)}"
        ),
    )

    live_energetic_path = (
        COMPARISON_FOLDER
        / "live_energetic.wav"
    )

    live_energetic_path.write_bytes(
        playback_response.content
    )

    live_metadata = read_wav_metadata(
        live_energetic_path
    )

    check(
        "Live Energetic output is mono",
        live_metadata["channels"]
        == 1,
        repr(
            live_metadata
        ),
    )

    check(
        "Live Energetic output is PCM16",
        live_metadata["sample_width"]
        == 2,
        repr(
            live_metadata
        ),
    )

    check(
        "Live Energetic output is 24 kHz",
        live_metadata["sample_rate"]
        == 24_000,
        repr(
            live_metadata
        ),
    )

    check(
        "Live Energetic output has meaningful duration",
        live_metadata[
            "duration_seconds"
        ]
        > 1.0,
        repr(
            live_metadata
        ),
    )

    check(
        "Live Energetic comparison copy was saved",
        (
            live_energetic_path.exists()
            and live_energetic_path.stat().st_size
            > 44
        ),
        str(
            live_energetic_path
        ),
    )

    # ========================================================
    # Fair same-source comparison
    # ========================================================

    neutral_same_source = (
        COMPARISON_FOLDER
        / "neutral_same_source.wav"
    )

    energetic_same_source = (
        COMPARISON_FOLDER
        / "energetic_same_source.wav"
    )

    processing_input = (
        COMPARISON_FOLDER
        / "_energetic_processing_input.wav"
    )

    shutil.copy2(
        SOURCE_NEUTRAL,
        neutral_same_source,
    )

    shutil.copy2(
        SOURCE_NEUTRAL,
        processing_input,
    )

    check(
        "Same-source Neutral copy was saved",
        (
            neutral_same_source.exists()
            and neutral_same_source.stat().st_size
            > 44
        ),
        str(
            neutral_same_source
        ),
    )

    energetic_controls = resolve_style_controls(
        style="energetic",
        speed=1.0,
        volume=1.0,
        bass=0.0,
    )

    check(
        "Energetic profile resolves to 1.08 speed",
        energetic_controls.effective_speed
        == 1.08,
        repr(
            energetic_controls
        ),
    )

    tts_service.apply_audio_controls(
        raw_audio=processing_input,
        final_audio=energetic_same_source,
        volume=(
            energetic_controls
            .effective_volume
        ),
        bass=(
            energetic_controls
            .effective_bass
        ),
        speed=(
            energetic_controls
            .effective_speed
        ),
        apply_speed=True,
    )

    processing_input.unlink(
        missing_ok=True
    )

    check(
        "Same-source Energetic output was created",
        (
            energetic_same_source.exists()
            and energetic_same_source.stat().st_size
            > 44
        ),
        str(
            energetic_same_source
        ),
    )

    neutral_metadata = read_wav_metadata(
        neutral_same_source
    )

    energetic_metadata = read_wav_metadata(
        energetic_same_source
    )

    same_source_metadata = {
        "neutral": neutral_metadata,
        "energetic": energetic_metadata,
    }

    check(
        "Both same-source outputs are mono",
        all(
            item["channels"] == 1
            for item
            in same_source_metadata.values()
        ),
        repr(
            same_source_metadata
        ),
    )

    check(
        "Both same-source outputs are PCM16",
        all(
            item["sample_width"] == 2
            for item
            in same_source_metadata.values()
        ),
        repr(
            same_source_metadata
        ),
    )

    check(
        "Both same-source outputs are 24 kHz",
        all(
            item["sample_rate"] == 24_000
            for item
            in same_source_metadata.values()
        ),
        repr(
            same_source_metadata
        ),
    )

    neutral_duration = float(
        neutral_metadata[
            "duration_seconds"
        ]
    )

    energetic_duration = float(
        energetic_metadata[
            "duration_seconds"
        ]
    )

    check(
        "Same-source Energetic is shorter than Neutral",
        energetic_duration
        < neutral_duration,
        repr(
            same_source_metadata
        ),
    )

    expected_energetic_duration = (
        neutral_duration
        / energetic_controls.effective_speed
    )

    check(
        "Same-source duration matches 1.08 speed",
        abs(
            energetic_duration
            - expected_energetic_duration
        )
        <= 0.10,
        (
            f"Expected≈"
            f"{expected_energetic_duration:.3f}; "
            f"Actual="
            f"{energetic_duration:.3f}"
        ),
    )

    check(
        "Same-source Neutral and Energetic bytes differ",
        neutral_same_source.read_bytes()
        != energetic_same_source.read_bytes(),
    )

    print()
    print("=" * 92)
    print("SAME-SOURCE STYLE COMPARISON")
    print("=" * 92)

    print(
        "Neutral duration  :",
        f"{neutral_duration:.3f}s",
    )

    print(
        "Energetic duration:",
        f"{energetic_duration:.3f}s",
    )

    print()
    print(
        "Neutral file:",
        neutral_same_source,
    )

    print(
        "Energetic file:",
        energetic_same_source,
    )

    print(
        "Live output:",
        live_energetic_path,
    )

    # ========================================================
    # Clean API history and normal output
    # ========================================================

    item_url = (
        f"{BASE_URL}/speech/history/"
        f"{generated_id}"
    )

    delete_response = requests.delete(
        item_url,
        timeout=30,
    )

    delete_result = response_json(
        delete_response
    )

    check(
        "Live generation deletion returned HTTP 200",
        delete_response.status_code
        == 200,
        repr(
            delete_result
        ),
    )

    check(
        "Live database record was deleted",
        delete_result[
            "database_record_deleted"
        ]
        is True,
        repr(
            delete_result
        ),
    )

    check(
        "Live original WAV was deleted",
        delete_result[
            "audio_file_deleted"
        ]
        is True,
        repr(
            delete_result
        ),
    )

    record_deleted = True

    check(
        "Live original output no longer exists",
        not generated_output_path.exists(),
        str(
            generated_output_path
        ),
    )

    pending_path = (
        generated_output_path.with_name(
            generated_output_path.name
            + ".delete_pending"
        )
    )

    check(
        "Live pending-delete file does not remain",
        not pending_path.exists(),
        str(
            pending_path
        ),
    )

    history_after_response = requests.get(
        history_url,
        timeout=30,
    )

    history_after = response_json(
        history_after_response
    )

    check(
        "History is readable after cleanup",
        (
            history_after_response.status_code
            == 200
            and isinstance(
                history_after,
                list,
            )
        ),
        repr(
            history_after
        ),
    )

    history_ids_after = {
        int(
            item["id"]
        )
        for item in history_after
    }

    check(
        "History returned to its original state",
        history_ids_after
        == history_ids_before,
        (
            f"Before={history_ids_before}; "
            f"After={history_ids_after}"
        ),
    )

    deleted_playback = requests.get(
        playback_url,
        timeout=20,
    )

    check(
        "Deleted playback URL returns HTTP 404",
        deleted_playback.status_code
        == 404,
        deleted_playback.text,
    )

    pending_after = {
        path.name
        for path in OUTPUT_FOLDER.glob(
            "*.delete_pending"
        )
    }

    check(
        "No new delete-pending orphan remains",
        not (
            pending_after
            - pending_before
        ),
        repr(
            pending_after
            - pending_before
        ),
    )

    report = {
        "milestone": "10.7D-5B",
        "created_at": datetime.now().isoformat(),
        "live_generation": generation,
        "live_metadata": live_metadata,
        "same_source": {
            "source": str(
                SOURCE_NEUTRAL
            ),
            "neutral_path": str(
                neutral_same_source
            ),
            "energetic_path": str(
                energetic_same_source
            ),
            "neutral_metadata": (
                neutral_metadata
            ),
            "energetic_metadata": (
                energetic_metadata
            ),
            "effective_controls": {
                "speed": (
                    energetic_controls
                    .effective_speed
                ),
                "volume": (
                    energetic_controls
                    .effective_volume
                ),
                "bass": (
                    energetic_controls
                    .effective_bass
                ),
            },
        },
    }

    REPORT_PATH.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )

    check(
        "Comparison report was saved",
        (
            REPORT_PATH.exists()
            and REPORT_PATH.stat().st_size
            > 0
        ),
        str(
            REPORT_PATH
        ),
    )

    print()
    print("=" * 92)
    print(
        "MILESTONE 10.7D-5B LIVE CORRECTED "
        "STYLE PIPELINE: PASSED"
    )
    print("=" * 92)

    print(
        "Checks passed:",
        checks_passed,
    )

    print()
    print(
        "Comparison folder:",
        COMPARISON_FOLDER,
    )

finally:
    if (
        generated_id is not None
        and not record_deleted
    ):
        try:
            emergency_response = requests.delete(
                (
                    f"{BASE_URL}/speech/history/"
                    f"{generated_id}"
                ),
                timeout=30,
            )

            print(
                "Emergency cleanup returned HTTP",
                emergency_response.status_code,
            )

        except Exception as cleanup_error:
            print(
                "Emergency cleanup failed:",
                cleanup_error,
            )
