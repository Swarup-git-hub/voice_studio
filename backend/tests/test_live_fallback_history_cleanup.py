from __future__ import annotations

import io
import json
import socket
import time
import wave
from pathlib import Path
from typing import Any

import requests

from app.core.config import settings


BASE_URL = "http://127.0.0.1:8000"
INDICF5_URL = "http://127.0.0.1:8002"

VOICE_ID = 10

TEST_TEXT = (
    "This fallback test verifies that speech generation "
    "continues working when the primary English engine "
    "is temporarily unavailable."
)

OUTPUT_FOLDER = Path(
    settings.OUTPUT_FOLDER
).expanduser().resolve()


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


def parse_json(
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


def port_is_open(
    host: str,
    port: int,
) -> bool:
    connection = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    )

    connection.settimeout(1.5)

    try:
        return (
            connection.connect_ex(
                (
                    host,
                    port,
                )
            )
            == 0
        )
    finally:
        connection.close()


print("=" * 92)
print(
    "MILESTONE 10.6.7E — LIVE FALLBACK, "
    "PLAYBACK, HISTORY AND CLEANUP REGRESSION"
)
print("=" * 92)

generation_id: int | None = None
output_path: Path | None = None
pending_delete_path: Path | None = None
deleted_successfully = False

pending_files_before = {
    path.name
    for path in OUTPUT_FOLDER.glob(
        "*.delete_pending"
    )
}

try:
    check(
        "CosyVoice port 8001 is stopped",
        not port_is_open(
            "127.0.0.1",
            8001,
        ),
        (
            "CosyVoice is still running. "
            "Stop only the CosyVoice terminal "
            "before running this test."
        ),
    )

    backend_response = requests.get(
        f"{BASE_URL}/health",
        timeout=15,
    )

    check(
        "Main backend is healthy",
        backend_response.status_code == 200,
        backend_response.text,
    )

    indic_response = requests.get(
        f"{INDICF5_URL}/health",
        timeout=30,
    )

    check(
        "IndicF5 service is healthy",
        indic_response.status_code == 200,
        indic_response.text,
    )

    indic_health = parse_json(
        indic_response
    )

    check(
        "IndicF5 model is loaded",
        bool(
            indic_health.get(
                "model_loaded",
                False,
            )
        ),
        repr(indic_health),
    )

    history_url = (
        f"{BASE_URL}/speech/history"
    )

    history_before_response = requests.get(
        history_url,
        timeout=15,
    )

    history_before = parse_json(
        history_before_response
    )

    check(
        "History is readable before fallback",
        (
            history_before_response.status_code
            == 200
            and isinstance(
                history_before,
                list,
            )
        ),
        repr(history_before),
    )

    before_ids = {
        int(item["id"])
        for item in history_before
    }

    payload = {
        "voice_id": VOICE_ID,
        "text": TEST_TEXT,
        "speed": 1.0,
        "volume": 1.0,
        "bass": 0.0,
        "engine": "auto",
        "allow_fallback": True,
    }

    print()
    print(
        "Submitting controlled fallback request..."
    )

    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
    )

    started_at = time.perf_counter()

    generation_response = requests.post(
        f"{BASE_URL}/speech/generate",
        json=payload,
        timeout=600,
    )

    elapsed_seconds = (
        time.perf_counter()
        - started_at
    )

    print()
    print(
        "Generation elapsed seconds:",
        round(
            elapsed_seconds,
            2,
        ),
    )

    generation = parse_json(
        generation_response
    )

    print(
        json.dumps(
            generation,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )

    check(
        "Fallback generation returned HTTP 200",
        generation_response.status_code == 200,
        repr(generation),
    )

    required_fields = {
        "id",
        "voice_id",
        "output_filename",
        "engine_requested",
        "engine_used",
        "fallback_used",
        "routing_reason",
        "detected_language",
        "audio_url",
        "download_url",
    }

    missing_fields = (
        required_fields
        - set(
            generation.keys()
        )
    )

    check(
        "Generation contains routing metadata",
        not missing_fields,
        (
            "Missing fields: "
            f"{sorted(missing_fields)}"
        ),
    )

    generation_id = int(
        generation["id"]
    )

    check(
        "Correct voice was used",
        int(
            generation["voice_id"]
        )
        == VOICE_ID,
    )

    check(
        "Auto routing was requested",
        generation["engine_requested"]
        == "auto",
        repr(
            generation["engine_requested"]
        ),
    )

    check(
        "IndicF5 handled the fallback",
        generation["engine_used"]
        == "indicf5",
        repr(
            generation["engine_used"]
        ),
    )

    check(
        "Fallback was recorded",
        generation["fallback_used"]
        is True,
        repr(
            generation["fallback_used"]
        ),
    )

    check(
        "English was detected",
        generation["detected_language"]
        == "english",
        repr(
            generation["detected_language"]
        ),
    )

    routing_reason = str(
        generation["routing_reason"]
    )

    check(
        "English CosyVoice primary route was recorded",
        routing_reason.startswith(
            "auto_english_cosyvoice_primary"
        ),
        routing_reason,
    )

    check(
        "CosyVoice unavailable fallback was recorded",
        (
            "fallback_after_cosyvoice_unavailable"
            in routing_reason
        ),
        routing_reason,
    )

    history_after_generation_response = (
        requests.get(
            history_url,
            timeout=15,
        )
    )

    history_after_generation = parse_json(
        history_after_generation_response
    )

    after_generation_ids = {
        int(item["id"])
        for item
        in history_after_generation
    }

    new_ids = (
        after_generation_ids
        - before_ids
    )

    check(
        "Exactly one fallback history row was created",
        new_ids == {
            generation_id
        },
        (
            f"Expected={{{generation_id}}}; "
            f"Actual={new_ids}"
        ),
    )

    item_url = (
        f"{BASE_URL}/speech/history/"
        f"{generation_id}"
    )

    item_response = requests.get(
        item_url,
        timeout=15,
    )

    history_item = parse_json(
        item_response
    )

    check(
        "Fallback history item is retrievable",
        item_response.status_code == 200,
        repr(history_item),
    )

    check(
        "Retrieved history ID is correct",
        int(
            history_item["id"]
        )
        == generation_id,
    )

    check(
        "History stores Auto as requested engine",
        history_item["engine_requested"]
        == "auto",
        repr(
            history_item["engine_requested"]
        ),
    )

    check(
        "History stores IndicF5 as used engine",
        history_item["engine_used"]
        == "indicf5",
        repr(
            history_item["engine_used"]
        ),
    )

    check(
        "History stores fallback usage",
        history_item["fallback_used"]
        is True,
        repr(
            history_item["fallback_used"]
        ),
    )

    check(
        "History stores the fallback reason",
        history_item["routing_reason"]
        == routing_reason,
        repr(
            history_item["routing_reason"]
        ),
    )

    output_path = (
        OUTPUT_FOLDER
        / generation["output_filename"]
    ).resolve()

    pending_delete_path = (
        output_path.with_name(
            output_path.name
            + ".delete_pending"
        )
    )

    check(
        "Fallback WAV exists in the output folder",
        output_path.exists(),
        str(output_path),
    )

    check(
        "Fallback WAV is non-empty on disk",
        (
            output_path.is_file()
            and output_path.stat().st_size
            > 44
        ),
        str(output_path),
    )

    audio_url = (
        f"{BASE_URL}/speech/history/"
        f"{generation_id}/audio"
    )

    playback_response = requests.get(
        audio_url,
        timeout=60,
    )

    playback_content_type = (
        playback_response.headers.get(
            "content-type",
            "",
        ).lower()
    )

    check(
        "Playback endpoint returned HTTP 200",
        playback_response.status_code == 200,
        playback_response.text[:500],
    )

    check(
        "Playback content type is audio",
        (
            "audio" in playback_content_type
            or "wav" in playback_content_type
            or "octet-stream"
            in playback_content_type
        ),
        playback_content_type,
    )

    check(
        "Playback returned non-empty audio",
        len(
            playback_response.content
        )
        > 44,
        (
            "Bytes="
            f"{len(playback_response.content)}"
        ),
    )

    download_url = (
        f"{BASE_URL}/speech/history/"
        f"{generation_id}/download"
    )

    download_response = requests.get(
        download_url,
        timeout=60,
    )

    content_disposition = (
        download_response.headers.get(
            "content-disposition",
            "",
        ).lower()
    )

    check(
        "Download endpoint returned HTTP 200",
        download_response.status_code == 200,
        download_response.text[:500],
    )

    check(
        "Download response is an attachment",
        "attachment" in content_disposition,
        content_disposition,
    )

    check(
        "Playback and download bytes are identical",
        (
            playback_response.content
            == download_response.content
        ),
        (
            "Playback bytes="
            f"{len(playback_response.content)}; "
            "Download bytes="
            f"{len(download_response.content)}"
        ),
    )

    with wave.open(
        io.BytesIO(
            playback_response.content
        ),
        "rb",
    ) as wav_file:
        metadata = {
            "channels": (
                wav_file.getnchannels()
            ),
            "sample_width": (
                wav_file.getsampwidth()
            ),
            "sample_rate": (
                wav_file.getframerate()
            ),
            "frames": (
                wav_file.getnframes()
            ),
            "duration_seconds": (
                wav_file.getnframes()
                / wav_file.getframerate()
            ),
        }

    check(
        "Fallback output is mono",
        metadata["channels"] == 1,
        repr(metadata),
    )

    check(
        "Fallback output is PCM16",
        metadata["sample_width"] == 2,
        repr(metadata),
    )

    check(
        "Fallback output is 24 kHz",
        metadata["sample_rate"] == 24_000,
        repr(metadata),
    )

    check(
        "Fallback output contains audio frames",
        metadata["frames"] > 0,
        repr(metadata),
    )

    check(
        "Fallback output has meaningful duration",
        metadata["duration_seconds"] > 1.0,
        repr(metadata),
    )

    print()
    print("Deleting temporary fallback generation...")

    delete_response = requests.delete(
        item_url,
        timeout=30,
    )

    delete_result = parse_json(
        delete_response
    )

    print(
        json.dumps(
            delete_result,
            ensure_ascii=False,
            indent=2,
        )
    )

    check(
        "Delete endpoint returned HTTP 200",
        delete_response.status_code == 200,
        repr(delete_result),
    )

    deleted_successfully = True

    check(
        "Delete response contains the correct ID",
        int(
            delete_result["generation_id"]
        )
        == generation_id,
        repr(delete_result),
    )

    check(
        "Database history row was deleted",
        delete_result[
            "database_record_deleted"
        ]
        is True,
        repr(delete_result),
    )

    check(
        "Generated WAV was deleted",
        delete_result[
            "audio_file_deleted"
        ]
        is True,
        repr(delete_result),
    )

    check(
        "Final output WAV no longer exists",
        not output_path.exists(),
        str(output_path),
    )

    check(
        "Pending-delete WAV no longer exists",
        not pending_delete_path.exists(),
        str(pending_delete_path),
    )

    pending_files_after = {
        path.name
        for path in OUTPUT_FOLDER.glob(
            "*.delete_pending"
        )
    }

    new_pending_files = (
        pending_files_after
        - pending_files_before
    )

    check(
        "No new delete-pending orphan remains",
        not new_pending_files,
        repr(new_pending_files),
    )

    deleted_item_response = requests.get(
        item_url,
        timeout=15,
    )

    check(
        "Deleted history item now returns HTTP 404",
        deleted_item_response.status_code == 404,
        deleted_item_response.text,
    )

    deleted_audio_response = requests.get(
        audio_url,
        timeout=15,
    )

    check(
        "Deleted playback URL now returns HTTP 404",
        deleted_audio_response.status_code == 404,
        deleted_audio_response.text,
    )

    deleted_download_response = requests.get(
        download_url,
        timeout=15,
    )

    check(
        "Deleted download URL now returns HTTP 404",
        deleted_download_response.status_code == 404,
        deleted_download_response.text,
    )

    history_final_response = requests.get(
        history_url,
        timeout=15,
    )

    history_final = parse_json(
        history_final_response
    )

    check(
        "History is readable after cleanup",
        (
            history_final_response.status_code
            == 200
            and isinstance(
                history_final,
                list,
            )
        ),
        repr(history_final),
    )

    final_ids = {
        int(item["id"])
        for item in history_final
    }

    check(
        "Deleted fallback ID is absent from history",
        generation_id not in final_ids,
        repr(final_ids),
    )

    check(
        "History returned to its original state",
        final_ids == before_ids,
        (
            f"Before={before_ids}; "
            f"After={final_ids}"
        ),
    )

    print()
    print("Fallback generation ID:", generation_id)
    print("Routing reason:", routing_reason)

    print(
        "WAV metadata:",
        json.dumps(
            metadata,
            indent=2,
        ),
    )

    print()
    print("=" * 92)
    print(
        "MILESTONE 10.6.7E LIVE FALLBACK, "
        "PLAYBACK, HISTORY AND CLEANUP: PASSED"
    )
    print("=" * 92)
    print("Checks passed:", checks_passed)

finally:
    if (
        generation_id is not None
        and not deleted_successfully
    ):
        print()
        print(
            "Attempting emergency cleanup for "
            f"generation ID {generation_id}..."
        )

        try:
            cleanup_response = requests.delete(
                (
                    f"{BASE_URL}/speech/history/"
                    f"{generation_id}"
                ),
                timeout=30,
            )

            print(
                "Emergency cleanup HTTP status:",
                cleanup_response.status_code,
            )
        except Exception as cleanup_error:
            print(
                "Emergency cleanup could not complete:",
                cleanup_error,
            )
