from __future__ import annotations

import json
import wave
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from app.audio.style_profiles import (
    STYLE_PROFILES,
)
from app.core.config import settings


BACKEND_ROOT = Path(__file__).resolve().parents[1]

BASE_URL = "http://127.0.0.1:8000"
COSYVOICE_URL = "http://127.0.0.1:8001"

VOICE_ID = 10

TEST_TEXT = (
    "Today we are testing an energetic delivery for a "
    "software engineering lesson. The browser sends a "
    "request, the server processes it, and the response "
    "returns in seconds. Let us understand what happens "
    "behind the scenes."
)

OUTPUT_FOLDER = Path(
    settings.OUTPUT_FOLDER
).expanduser().resolve()

COMPARISON_ROOT = (
    BACKEND_ROOT
    / "milestone_reports"
    / "style_comparisons"
)

TIMESTAMP = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

COMPARISON_FOLDER = (
    COMPARISON_ROOT
    / f"milestone10_7d5f_{TIMESTAMP}"
)

REPORT_PATH = (
    COMPARISON_FOLDER
    / "live_candidate_b_report.json"
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
        "file_size": path.stat().st_size,
    }


print("=" * 92)
print(
    "MILESTONE 10.7D-5F — LIVE CANDIDATE B "
    "PRODUCTION ACCEPTANCE"
)
print("=" * 92)

COMPARISON_FOLDER.mkdir(
    parents=True,
    exist_ok=True,
)

energetic_profile = STYLE_PROFILES[
    "energetic"
]

check(
    "Production Energetic speed is 1.025",
    energetic_profile.speed_multiplier
    == 1.025,
)

check(
    "Production Energetic volume is neutral",
    energetic_profile.volume_multiplier
    == 1.0,
)

check(
    "Production Energetic bass is neutral",
    energetic_profile.bass_offset_db
    == 0.0,
)

check(
    "Production presence gain is 0.8 dB",
    energetic_profile.presence_gain_db
    == 0.8,
)

check(
    "Production presence frequency is 2800 Hz",
    energetic_profile.presence_frequency_hz
    == 2800,
)

check(
    "Production presence Q is 1.2",
    energetic_profile.presence_q
    == 1.2,
)

generated_items: list[
    dict[str, Any]
] = []

deleted_ids: set[int] = set()

pending_before = {
    path.name
    for path in OUTPUT_FOLDER.glob(
        "*.delete_pending"
    )
}

history_url = (
    f"{BASE_URL}/speech/history"
)

try:
    # ========================================================
    # Service health
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

    history_before_response = requests.get(
        history_url,
        timeout=30,
    )

    history_before = parse_json(
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
    # Generate Neutral and Candidate B Energetic
    # ========================================================

    for style_name in (
        "neutral",
        "energetic",
    ):
        print()
        print("=" * 92)
        print(
            f"LIVE {style_name.upper()} GENERATION"
        )
        print("=" * 92)

        payload = {
            "voice_id": VOICE_ID,
            "text": TEST_TEXT,
            "speed": 1.0,
            "volume": 1.0,
            "bass": 0.0,
            "style": style_name,
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

        generation_response = requests.post(
            f"{BASE_URL}/speech/generate",
            json=payload,
            timeout=600,
        )

        generation = parse_json(
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
            f"{style_name} generation returned HTTP 200",
            generation_response.status_code
            == 200,
            repr(
                generation
            ),
        )

        check(
            f"{style_name} response stores the requested style",
            generation.get(
                "style"
            )
            == style_name,
            repr(
                generation.get(
                    "style"
                )
            ),
        )

        check(
            f"{style_name} preserves requested controls",
            (
                float(
                    generation.get(
                        "speed"
                    )
                )
                == 1.0
                and float(
                    generation.get(
                        "volume"
                    )
                )
                == 1.0
                and float(
                    generation.get(
                        "bass"
                    )
                )
                == 0.0
            ),
            repr(
                {
                    "speed": generation.get(
                        "speed"
                    ),
                    "volume": generation.get(
                        "volume"
                    ),
                    "bass": generation.get(
                        "bass"
                    ),
                }
            ),
        )

        check(
            f"{style_name} uses explicit CosyVoice without fallback",
            (
                generation.get(
                    "engine_requested"
                )
                == "cosyvoice"
                and generation.get(
                    "engine_used"
                )
                == "cosyvoice"
                and generation.get(
                    "fallback_used"
                )
                is False
            ),
            repr(
                {
                    "engine_requested": (
                        generation.get(
                            "engine_requested"
                        )
                    ),
                    "engine_used": (
                        generation.get(
                            "engine_used"
                        )
                    ),
                    "fallback_used": (
                        generation.get(
                            "fallback_used"
                        )
                    ),
                }
            ),
        )

        generation_id = int(
            generation[
                "id"
            ]
        )

        check(
            f"{style_name} generation ID is new",
            generation_id
            not in history_ids_before,
            str(
                generation_id
            ),
        )

        output_path = (
            OUTPUT_FOLDER
            / generation[
                "output_filename"
            ]
        ).resolve()

        check(
            f"{style_name} original WAV exists",
            (
                output_path.exists()
                and output_path.is_file()
                and output_path.stat().st_size
                > 44
            ),
            str(
                output_path
            ),
        )

        playback_url = (
            f"{BASE_URL}/speech/history/"
            f"{generation_id}/audio"
        )

        playback_response = requests.get(
            playback_url,
            timeout=60,
        )

        check(
            f"{style_name} playback returned HTTP 200",
            playback_response.status_code
            == 200,
            playback_response.text[:500],
        )

        check(
            f"{style_name} playback contains audio bytes",
            len(
                playback_response.content
            )
            > 44,
            (
                "Bytes="
                f"{len(playback_response.content)}"
            ),
        )

        comparison_path = (
            COMPARISON_FOLDER
            / f"{style_name}.wav"
        )

        comparison_path.write_bytes(
            playback_response.content
        )

        check(
            f"{style_name} comparison copy was saved",
            (
                comparison_path.exists()
                and comparison_path.stat().st_size
                > 44
            ),
            str(
                comparison_path
            ),
        )

        metadata = read_wav_metadata(
            comparison_path
        )

        check(
            f"{style_name} output is mono",
            metadata[
                "channels"
            ]
            == 1,
            repr(
                metadata
            ),
        )

        check(
            f"{style_name} output is PCM16",
            metadata[
                "sample_width"
            ]
            == 2,
            repr(
                metadata
            ),
        )

        check(
            f"{style_name} output is 24 kHz",
            metadata[
                "sample_rate"
            ]
            == 24_000,
            repr(
                metadata
            ),
        )

        check(
            f"{style_name} output has meaningful duration",
            metadata[
                "duration_seconds"
            ]
            > 1.0,
            repr(
                metadata
            ),
        )

        generated_items.append(
            {
                "style": style_name,
                "id": generation_id,
                "generation": generation,
                "output_path": output_path,
                "playback_url": playback_url,
                "comparison_path": (
                    comparison_path
                ),
                "metadata": metadata,
                "audio_bytes": (
                    playback_response.content
                ),
            }
        )

    # ========================================================
    # Pair verification
    # ========================================================

    generated_ids = {
        item[
            "id"
        ]
        for item in generated_items
    }

    check(
        "Exactly two new generation IDs were created",
        (
            len(
                generated_items
            )
            == 2
            and len(
                generated_ids
            )
            == 2
        ),
        repr(
            generated_ids
        ),
    )

    neutral_item = next(
        item
        for item in generated_items
        if item[
            "style"
        ]
        == "neutral"
    )

    energetic_item = next(
        item
        for item in generated_items
        if item[
            "style"
        ]
        == "energetic"
    )

    check(
        "Neutral and Energetic WAV bytes differ",
        neutral_item[
            "audio_bytes"
        ]
        != energetic_item[
            "audio_bytes"
        ],
    )

    print()
    print("=" * 92)
    print("LIVE COMPARISON")
    print("=" * 92)

    print(
        "Neutral duration  :",
        (
            f"{neutral_item['metadata']['duration_seconds']:.3f}s"
        ),
    )

    print(
        "Energetic duration:",
        (
            f"{energetic_item['metadata']['duration_seconds']:.3f}s"
        ),
    )

    print()
    print(
        "Neutral file:",
        neutral_item[
            "comparison_path"
        ],
    )

    print(
        "Energetic file:",
        energetic_item[
            "comparison_path"
        ],
    )

    # ========================================================
    # API and output cleanup
    # ========================================================

    for item in generated_items:
        generation_id = item[
            "id"
        ]

        delete_response = requests.delete(
            (
                f"{BASE_URL}/speech/history/"
                f"{generation_id}"
            ),
            timeout=30,
        )

        delete_result = parse_json(
            delete_response
        )

        check(
            (
                item[
                    "style"
                ]
                + " deletion returned HTTP 200"
            ),
            delete_response.status_code
            == 200,
            repr(
                delete_result
            ),
        )

        check(
            (
                item[
                    "style"
                ]
                + " database row and original WAV were deleted"
            ),
            (
                delete_result.get(
                    "database_record_deleted"
                )
                is True
                and delete_result.get(
                    "audio_file_deleted"
                )
                is True
            ),
            repr(
                delete_result
            ),
        )

        deleted_ids.add(
            generation_id
        )

    check(
        "Both original output WAV files were removed",
        all(
            not item[
                "output_path"
            ].exists()
            for item in generated_items
        ),
        repr(
            [
                str(
                    item[
                        "output_path"
                    ]
                )
                for item in generated_items
                if item[
                    "output_path"
                ].exists()
            ]
        ),
    )

    history_after_response = requests.get(
        history_url,
        timeout=30,
    )

    history_after = parse_json(
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

    deleted_playback_statuses = []

    for item in generated_items:
        deleted_response = requests.get(
            item[
                "playback_url"
            ],
            timeout=20,
        )

        deleted_playback_statuses.append(
            deleted_response.status_code
        )

    check(
        "Both deleted playback URLs return HTTP 404",
        deleted_playback_statuses
        == [
            404,
            404,
        ],
        repr(
            deleted_playback_statuses
        ),
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
        "milestone": "10.7D-5F",
        "created_at": (
            datetime.now().isoformat()
        ),
        "production_energetic_profile": {
            "speed_multiplier": (
                energetic_profile
                .speed_multiplier
            ),
            "volume_multiplier": (
                energetic_profile
                .volume_multiplier
            ),
            "bass_offset_db": (
                energetic_profile
                .bass_offset_db
            ),
            "presence_gain_db": (
                energetic_profile
                .presence_gain_db
            ),
            "presence_frequency_hz": (
                energetic_profile
                .presence_frequency_hz
            ),
            "presence_q": (
                energetic_profile
                .presence_q
            ),
        },
        "test_text": TEST_TEXT,
        "neutral": {
            "generation": (
                neutral_item[
                    "generation"
                ]
            ),
            "metadata": (
                neutral_item[
                    "metadata"
                ]
            ),
            "comparison_path": str(
                neutral_item[
                    "comparison_path"
                ]
            ),
        },
        "energetic": {
            "generation": (
                energetic_item[
                    "generation"
                ]
            ),
            "metadata": (
                energetic_item[
                    "metadata"
                ]
            ),
            "comparison_path": str(
                energetic_item[
                    "comparison_path"
                ]
            ),
        },
        "history_restored": (
            history_ids_after
            == history_ids_before
        ),
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
        "Live acceptance report was saved",
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
        "MILESTONE 10.7D-5F LIVE CANDIDATE B "
        "PIPELINE: PASSED"
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
    for item in generated_items:
        generation_id = item[
            "id"
        ]

        if generation_id in deleted_ids:
            continue

        try:
            emergency_response = requests.delete(
                (
                    f"{BASE_URL}/speech/history/"
                    f"{generation_id}"
                ),
                timeout=30,
            )

            print(
                "Emergency cleanup for",
                generation_id,
                "returned HTTP",
                emergency_response.status_code,
            )

        except Exception as cleanup_error:
            print(
                "Emergency cleanup failed for",
                generation_id,
                ":",
                cleanup_error,
            )
