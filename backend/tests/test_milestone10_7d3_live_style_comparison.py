from __future__ import annotations

import io
import json
import socket
import time
import wave
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from app.core.config import settings


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent

FRONTEND_APP_PATH = (
    PROJECT_ROOT
    / "frontend"
    / "src"
    / "App.jsx"
)

OUTPUT_FOLDER = Path(
    settings.OUTPUT_FOLDER
).expanduser().resolve()

COMPARISON_ROOT = (
    BACKEND_ROOT
    / "milestone_reports"
    / "style_comparisons"
)

BASE_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://127.0.0.1:5173"
COSYVOICE_URL = "http://127.0.0.1:8001"

VOICE_ID = 10

TEST_TEXT = (
    "This live comparison demonstrates how one saved voice "
    "can use different delivery styles while preserving the "
    "original script, selected engine, and generated history."
)

STYLES = (
    "neutral",
    "energetic",
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


def read_wav_metadata(
    content: bytes,
) -> dict[str, float | int]:
    with wave.open(
        io.BytesIO(content),
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
    "MILESTONE 10.7D-3 — LIVE NEUTRAL "
    "VERSUS ENERGETIC STYLE COMPARISON"
)
print("=" * 92)

generated_ids: list[int] = []
deleted_ids: set[int] = set()

results: dict[
    str,
    dict[str, Any],
] = {}

pending_files_before = {
    path.name
    for path in OUTPUT_FOLDER.glob(
        "*.delete_pending"
    )
}

comparison_timestamp = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

comparison_folder = (
    COMPARISON_ROOT
    / f"milestone10_7d3_{comparison_timestamp}"
)

comparison_folder.mkdir(
    parents=True,
    exist_ok=True,
)

try:
    # ========================================================
    # Verify Milestone 10.7D-2 frontend integration
    # ========================================================

    check(
        "Frontend App.jsx exists",
        FRONTEND_APP_PATH.exists(),
        str(FRONTEND_APP_PATH),
    )

    frontend_source = (
        FRONTEND_APP_PATH.read_text(
            encoding="utf-8-sig",
        )
    )

    check(
        "Frontend contains the locked style map",
        "const STYLE_LABELS = {"
        in frontend_source,
    )

    check(
        "Frontend style state defaults to neutral",
        (
            'const [style, setStyle] '
            '= useState("neutral");'
            in frontend_source
        ),
    )

    check(
        "Frontend sends style in generation payload",
        "        style,\n"
        in frontend_source,
    )

    check(
        "Frontend contains the style selector",
        (
            '<span className="field-label">'
            "Voice style</span>"
            in frontend_source
        ),
    )

    check(
        "Latest preview displays style",
        (
            "Style: "
            "{formatStyle(latestGeneration.style)}"
            in frontend_source
        ),
    )

    check(
        "Generated history displays style",
        (
            "Style: "
            "{formatStyle(item.style)}"
            in frontend_source
        ),
    )

    # ========================================================
    # Service health
    # ========================================================

    frontend_response = requests.get(
        FRONTEND_URL,
        timeout=20,
    )

    check(
        "Frontend development server is reachable",
        frontend_response.status_code == 200,
        frontend_response.text[:500],
    )

    backend_response = requests.get(
        f"{BASE_URL}/health",
        timeout=20,
    )

    check(
        "Main backend is healthy",
        backend_response.status_code == 200,
        backend_response.text,
    )

    cosyvoice_response = requests.get(
        f"{COSYVOICE_URL}/health",
        timeout=30,
    )

    check(
        "CosyVoice service is healthy",
        cosyvoice_response.status_code == 200,
        cosyvoice_response.text,
    )

    history_url = (
        f"{BASE_URL}/speech/history"
    )

    history_before_response = requests.get(
        history_url,
        timeout=30,
    )

    history_before = parse_json(
        history_before_response
    )

    check(
        "History is readable before comparison",
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

    history_ids_before = {
        int(item["id"])
        for item in history_before
    }

    # ========================================================
    # Generate Neutral and Energetic versions
    # ========================================================

    for style in STYLES:
        print()
        print("-" * 92)
        print(
            f"GENERATING STYLE: {style.upper()}"
        )
        print("-" * 92)

        payload = {
            "voice_id": VOICE_ID,
            "text": TEST_TEXT,
            "speed": 1.0,
            "volume": 1.0,
            "bass": 0.0,
            "style": style,
            "engine": "cosyvoice",
            "allow_fallback": False,
        }

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

        generation = parse_json(
            generation_response
        )

        print()
        print(
            "Elapsed seconds:",
            round(
                elapsed_seconds,
                2,
            ),
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
            f"{style} generation returned HTTP 200",
            generation_response.status_code
            == 200,
            repr(generation),
        )

        required_fields = {
            "id",
            "voice_id",
            "output_filename",
            "speed",
            "volume",
            "bass",
            "style",
            "engine_requested",
            "engine_used",
            "fallback_used",
            "detected_language",
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
            f"{style} response contains required metadata",
            not missing_fields,
            (
                "Missing fields: "
                f"{sorted(missing_fields)}"
            ),
        )

        generation_id = int(
            generation["id"]
        )

        generated_ids.append(
            generation_id
        )

        check(
            f"{style} response stores the requested style",
            generation["style"]
            == style,
            repr(
                generation["style"]
            ),
        )

        check(
            f"{style} response preserves requested controls",
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
            f"{style} requested explicit CosyVoice",
            generation[
                "engine_requested"
            ]
            == "cosyvoice",
            repr(
                generation[
                    "engine_requested"
                ]
            ),
        )

        check(
            f"{style} used CosyVoice",
            generation[
                "engine_used"
            ]
            == "cosyvoice",
            repr(
                generation[
                    "engine_used"
                ]
            ),
        )

        check(
            f"{style} did not use fallback",
            generation[
                "fallback_used"
            ]
            is False,
            repr(
                generation[
                    "fallback_used"
                ]
            ),
        )

        check(
            f"{style} detected English",
            generation[
                "detected_language"
            ]
            == "english",
            repr(
                generation[
                    "detected_language"
                ]
            ),
        )

        check(
            f"{style} generation ID is new",
            generation_id
            not in history_ids_before,
            str(generation_id),
        )

        output_path = (
            OUTPUT_FOLDER
            / generation[
                "output_filename"
            ]
        ).resolve()

        check(
            f"{style} WAV exists in output folder",
            (
                output_path.exists()
                and output_path.is_file()
                and output_path.stat().st_size
                > 44
            ),
            str(output_path),
        )

        item_url = (
            f"{BASE_URL}/speech/history/"
            f"{generation_id}"
        )

        item_response = requests.get(
            item_url,
            timeout=30,
        )

        history_item = parse_json(
            item_response
        )

        check(
            f"{style} history item is retrievable",
            item_response.status_code
            == 200,
            repr(history_item),
        )

        check(
            f"{style} history item persists style",
            history_item[
                "style"
            ]
            == style,
            repr(
                history_item[
                    "style"
                ]
            ),
        )

        audio_url = (
            f"{BASE_URL}/speech/history/"
            f"{generation_id}/audio"
        )

        playback_response = requests.get(
            audio_url,
            timeout=60,
        )

        check(
            f"{style} playback returned HTTP 200",
            playback_response.status_code
            == 200,
            playback_response.text[:500],
        )

        check(
            f"{style} playback returned audio bytes",
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

        check(
            f"{style} download returned HTTP 200",
            download_response.status_code
            == 200,
            download_response.text[:500],
        )

        check(
            f"{style} playback and download match",
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

        metadata = read_wav_metadata(
            playback_response.content
        )

        check(
            f"{style} output is mono",
            metadata["channels"]
            == 1,
            repr(metadata),
        )

        check(
            f"{style} output is PCM16",
            metadata["sample_width"]
            == 2,
            repr(metadata),
        )

        check(
            f"{style} output is 24 kHz",
            metadata["sample_rate"]
            == 24_000,
            repr(metadata),
        )

        check(
            f"{style} output has meaningful duration",
            metadata[
                "duration_seconds"
            ]
            > 1.0,
            repr(metadata),
        )

        comparison_path = (
            comparison_folder
            / f"{style}.wav"
        )

        comparison_path.write_bytes(
            playback_response.content
        )

        results[style] = {
            "generation_id": generation_id,
            "generation": generation,
            "history_item": history_item,
            "output_path": output_path,
            "item_url": item_url,
            "audio_url": audio_url,
            "download_url": download_url,
            "audio_bytes": (
                playback_response.content
            ),
            "metadata": metadata,
            "comparison_path": (
                comparison_path
            ),
            "elapsed_seconds": (
                elapsed_seconds
            ),
        }

    # ========================================================
    # Compare results and history
    # ========================================================

    check(
        "Neutral and Energetic use different generation IDs",
        (
            results[
                "neutral"
            ][
                "generation_id"
            ]
            != results[
                "energetic"
            ][
                "generation_id"
            ]
        ),
    )

    history_after_generation_response = (
        requests.get(
            history_url,
            timeout=30,
        )
    )

    history_after_generation = parse_json(
        history_after_generation_response
    )

    new_history_ids = {
        int(item["id"])
        for item
        in history_after_generation
    } - history_ids_before

    check(
        "Exactly two comparison history rows were created",
        new_history_ids
        == set(
            generated_ids
        ),
        (
            f"Expected={set(generated_ids)}; "
            f"Actual={new_history_ids}"
        ),
    )

    check(
        "Neutral and Energetic WAV bytes differ",
        (
            results[
                "neutral"
            ][
                "audio_bytes"
            ]
            != results[
                "energetic"
            ][
                "audio_bytes"
            ]
        ),
    )

    neutral_copy = results[
        "neutral"
    ][
        "comparison_path"
    ]

    energetic_copy = results[
        "energetic"
    ][
        "comparison_path"
    ]

    check(
        "Neutral comparison copy was saved",
        (
            neutral_copy.exists()
            and neutral_copy.stat().st_size
            > 44
        ),
        str(neutral_copy),
    )

    check(
        "Energetic comparison copy was saved",
        (
            energetic_copy.exists()
            and energetic_copy.stat().st_size
            > 44
        ),
        str(energetic_copy),
    )

    check(
        "Neutral comparison copy matches playback",
        (
            neutral_copy.read_bytes()
            == results[
                "neutral"
            ][
                "audio_bytes"
            ]
        ),
    )

    check(
        "Energetic comparison copy matches playback",
        (
            energetic_copy.read_bytes()
            == results[
                "energetic"
            ][
                "audio_bytes"
            ]
        ),
    )

    print()
    print("=" * 92)
    print("LIVE STYLE COMPARISON")
    print("=" * 92)

    for style in STYLES:
        metadata = results[
            style
        ][
            "metadata"
        ]

        print()
        print(
            f"{style.upper()} ID:",
            results[
                style
            ][
                "generation_id"
            ],
        )

        print(
            "Duration:",
            round(
                float(
                    metadata[
                        "duration_seconds"
                    ]
                ),
                3,
            ),
            "seconds",
        )

        print(
            "Generation elapsed:",
            round(
                float(
                    results[
                        style
                    ][
                        "elapsed_seconds"
                    ]
                ),
                2,
            ),
            "seconds",
        )

        print(
            "Comparison copy:",
            results[
                style
            ][
                "comparison_path"
            ],
        )

    # ========================================================
    # Delete temporary records and original WAV files
    # ========================================================

    print()
    print("Cleaning temporary generations...")

    for style in STYLES:
        result = results[
            style
        ]

        delete_response = requests.delete(
            result[
                "item_url"
            ],
            timeout=30,
        )

        delete_result = parse_json(
            delete_response
        )

        check(
            f"{style} deletion returned HTTP 200",
            delete_response.status_code
            == 200,
            repr(delete_result),
        )

        check(
            f"{style} database record was deleted",
            delete_result[
                "database_record_deleted"
            ]
            is True,
            repr(delete_result),
        )

        check(
            f"{style} original WAV was deleted",
            delete_result[
                "audio_file_deleted"
            ]
            is True,
            repr(delete_result),
        )

        deleted_ids.add(
            result[
                "generation_id"
            ]
        )

        check(
            f"{style} original output no longer exists",
            not result[
                "output_path"
            ].exists(),
            str(
                result[
                    "output_path"
                ]
            ),
        )

        pending_path = (
            result[
                "output_path"
            ].with_name(
                result[
                    "output_path"
                ].name
                + ".delete_pending"
            )
        )

        check(
            f"{style} pending-delete file does not remain",
            not pending_path.exists(),
            str(pending_path),
        )

    history_final_response = requests.get(
        history_url,
        timeout=30,
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

    history_ids_final = {
        int(item["id"])
        for item in history_final
    }

    check(
        "History returned to its original state",
        history_ids_final
        == history_ids_before,
        (
            f"Before={history_ids_before}; "
            f"After={history_ids_final}"
        ),
    )

    for style in STYLES:
        deleted_audio_response = requests.get(
            results[
                style
            ][
                "audio_url"
            ],
            timeout=20,
        )

        check(
            f"{style} deleted playback URL returns HTTP 404",
            deleted_audio_response.status_code
            == 404,
            deleted_audio_response.text,
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

    print()
    print("=" * 92)
    print(
        "MILESTONE 10.7D-3 LIVE STYLE "
        "COMPARISON: PASSED"
    )
    print("=" * 92)
    print("Checks passed:", checks_passed)
    print()
    print(
        "Comparison folder:",
        comparison_folder,
    )

finally:
    for generation_id in generated_ids:
        if generation_id in deleted_ids:
            continue

        try:
            cleanup_response = requests.delete(
                (
                    f"{BASE_URL}/speech/history/"
                    f"{generation_id}"
                ),
                timeout=30,
            )

            print(
                "Emergency cleanup for generation",
                generation_id,
                "returned HTTP",
                cleanup_response.status_code,
            )

        except Exception as cleanup_error:
            print(
                "Emergency cleanup failed for generation",
                generation_id,
                ":",
                cleanup_error,
            )
