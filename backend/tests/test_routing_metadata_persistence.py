from __future__ import annotations

import json
import secrets
import sqlite3
import wave
from pathlib import Path
from typing import Any

import requests

from app.core.config import settings


BASE_URL = "http://127.0.0.1:8000"
INDICF5_URL = "http://127.0.0.1:8002"
VOICE_ID = 10

TEST_TOKEN = str(
    secrets.randbelow(90000000) + 10000000
)

TEST_TEXT = (
    "ఇది రూటింగ్ మెటాడేటా నిల్వ పరీక్ష. "
    f"పరీక్ష సంఖ్య {TEST_TOKEN}."
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


backend_root = Path.cwd().resolve()
database_path = backend_root / "voice.db"

output_folder = Path(
    settings.OUTPUT_FOLDER
).resolve()

generation_id: int | None = None
output_path: Path | None = None
history_before: int | None = None

generate_data: dict[str, Any] | None = None
history_data: dict[str, Any] | None = None
delete_data: dict[str, Any] | None = None


def count_history() -> int:
    with sqlite3.connect(
        str(database_path),
        timeout=30,
    ) as connection:
        return int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM generated_audio
                """
            ).fetchone()[0]
        )


def get_database_row(
    row_id: int,
) -> tuple[Any, ...] | None:
    with sqlite3.connect(
        str(database_path),
        timeout=30,
    ) as connection:
        return connection.execute(
            """
            SELECT
                id,
                engine_requested,
                engine_used,
                fallback_used,
                routing_reason
            FROM generated_audio
            WHERE id = ?
            """,
            (row_id,),
        ).fetchone()


try:
    print("=" * 80)
    print("ROUTING METADATA PERSISTENCE TEST")
    print("=" * 80)

    require(
        database_path.exists(),
        f"Database not found: {database_path}",
    )

    output_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    backend_health = requests.get(
        f"{BASE_URL}/health",
        timeout=(5, 20),
    )

    require(
        backend_health.status_code == 200,
        (
            "Main backend health check failed. "
            f"Status={backend_health.status_code}"
        ),
    )

    indic_health = requests.get(
        f"{INDICF5_URL}/health",
        timeout=(5, 30),
    )

    require(
        indic_health.status_code == 200,
        (
            "IndicF5 health check failed. "
            f"Status={indic_health.status_code}"
        ),
    )

    indic_health_data = indic_health.json()

    require(
        indic_health_data.get("status")
        == "healthy",
        "IndicF5 did not report healthy status.",
    )

    require(
        indic_health_data.get("model_loaded")
        is True,
        "IndicF5 model is not loaded.",
    )

    history_before = count_history()

    print("Voice ID:", VOICE_ID)
    print("Test token:", TEST_TOKEN)
    print("History before:", history_before)

    payload = {
        "voice_id": VOICE_ID,
        "text": TEST_TEXT,
        "speed": 1.0,
        "volume": 1.0,
        "bass": 0.0,
        "engine": "indicf5",
        "allow_fallback": False,
    }

    print("\nGENERATION REQUEST")
    print("-" * 80)
    display_json(payload)

    generate_response = requests.post(
        f"{BASE_URL}/speech/generate",
        json=payload,
        timeout=(10, 900),
    )

    print("\nGENERATION RESPONSE")
    print("-" * 80)
    print(
        "Status code:",
        generate_response.status_code,
    )

    try:
        parsed_generate_data = (
            generate_response.json()
        )
    except ValueError:
        parsed_generate_data = {
            "raw_body": generate_response.text,
        }

    display_json(parsed_generate_data)

    require(
        generate_response.status_code == 200,
        (
            "Speech generation failed. "
            f"Status={generate_response.status_code}; "
            f"Body={generate_response.text}"
        ),
    )

    require(
        isinstance(
            parsed_generate_data,
            dict,
        ),
        "Generation response is not a JSON object.",
    )

    generate_data = parsed_generate_data

    generation_id = int(
        generate_data["id"]
    )

    output_path = (
        output_folder
        / str(generate_data["output_filename"])
    ).resolve()

    require(
        output_path.parent == output_folder,
        "Output resolved outside the output folder.",
    )

    require(
        output_path.exists(),
        "Generated output file does not exist.",
    )

    require(
        output_path.stat().st_size > 0,
        "Generated output file is empty.",
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
        count_history()
    )

    database_row = get_database_row(
        generation_id
    )

    require(
        database_row is not None,
        "Generated record was not saved in SQLite.",
    )

    (
        database_id,
        database_engine_requested,
        database_engine_used,
        database_fallback_used,
        database_routing_reason,
    ) = database_row

    print("\nDATABASE METADATA")
    print("-" * 80)
    print("ID:", database_id)
    print(
        "engine_requested:",
        database_engine_requested,
    )
    print(
        "engine_used:",
        database_engine_used,
    )
    print(
        "fallback_used:",
        database_fallback_used,
    )
    print(
        "routing_reason:",
        database_routing_reason,
    )

    history_response = requests.get(
        (
            f"{BASE_URL}/speech/history/"
            f"{generation_id}"
        ),
        timeout=(5, 30),
    )

    print("\nHISTORY ITEM RESPONSE")
    print("-" * 80)
    print(
        "Status code:",
        history_response.status_code,
    )

    try:
        parsed_history_data = (
            history_response.json()
        )
    except ValueError:
        parsed_history_data = {
            "raw_body": history_response.text,
        }

    display_json(parsed_history_data)

    require(
        history_response.status_code == 200,
        (
            "History item request failed. "
            f"Status={history_response.status_code}; "
            f"Body={history_response.text}"
        ),
    )

    require(
        isinstance(
            parsed_history_data,
            dict,
        ),
        "History response is not a JSON object.",
    )

    history_data = parsed_history_data

    print("\nAUDIO VALIDATION")
    print("-" * 80)
    print("Output:", output_path)
    print("Size:", output_path.stat().st_size)
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
        "Generation HTTP success": (
            generate_data.get("status")
            == "success"
        ),
        "Generation engine requested": (
            generate_data.get(
                "engine_requested"
            )
            == "indicf5"
        ),
        "Generation engine used": (
            generate_data.get(
                "engine_used"
            )
            == "indicf5"
        ),
        "Generation no fallback": (
            generate_data.get(
                "fallback_used"
            )
            is False
        ),
        "Generation routing reason": (
            generate_data.get(
                "routing_reason"
            )
            == "explicit_indicf5"
        ),
        "Telugu detected": (
            generate_data.get(
                "detected_language"
            )
            == "telugu"
        ),
        "One history row added": (
            history_after_generation
            == history_before + 1
        ),
        "SQLite row ID correct": (
            database_id
            == generation_id
        ),
        "SQLite engine requested": (
            database_engine_requested
            == "indicf5"
        ),
        "SQLite engine used": (
            database_engine_used
            == "indicf5"
        ),
        "SQLite no fallback": (
            int(
                database_fallback_used
            )
            == 0
        ),
        "SQLite routing reason": (
            database_routing_reason
            == "explicit_indicf5"
        ),
        "History item ID correct": (
            history_data.get("id")
            == generation_id
        ),
        "History engine requested": (
            history_data.get(
                "engine_requested"
            )
            == "indicf5"
        ),
        "History engine used": (
            history_data.get(
                "engine_used"
            )
            == "indicf5"
        ),
        "History no fallback": (
            history_data.get(
                "fallback_used"
            )
            is False
        ),
        "History routing reason": (
            history_data.get(
                "routing_reason"
            )
            == "explicit_indicf5"
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
            "Metadata persistence checks failed: "
            + ", ".join(failed_checks)
        )

    print("\n" + "=" * 80)
    print("ROUTING METADATA PERSISTENCE: PASSED")
    print("=" * 80)

    delete_response = requests.delete(
        (
            f"{BASE_URL}/speech/history/"
            f"{generation_id}"
        ),
        timeout=(5, 30),
    )

    print("\nDELETE RESPONSE")
    print("-" * 80)
    print(
        "Status code:",
        delete_response.status_code,
    )

    try:
        parsed_delete_data = (
            delete_response.json()
        )
    except ValueError:
        parsed_delete_data = {
            "raw_body": delete_response.text,
        }

    display_json(parsed_delete_data)

    require(
        delete_response.status_code == 200,
        (
            "HTTP cleanup delete failed. "
            f"Status={delete_response.status_code}; "
            f"Body={delete_response.text}"
        ),
    )

    require(
        isinstance(
            parsed_delete_data,
            dict,
        ),
        "Delete response is not a JSON object.",
    )

    delete_data = parsed_delete_data

    require(
        delete_data.get(
            "database_record_deleted"
        )
        is True,
        "Delete API did not confirm database deletion.",
    )

    require(
        get_database_row(
            generation_id
        )
        is None,
        "Generated metadata row still exists after deletion.",
    )

    require(
        not output_path.exists(),
        "Generated WAV still exists after deletion.",
    )

    history_after_delete = count_history()

    require(
        history_after_delete
        == history_before,
        (
            "History count was not restored. "
            f"Before={history_before}, "
            f"After={history_after_delete}."
        ),
    )

    print("\nHTTP CLEANUP")
    print("-" * 80)
    print(
        "Database record deleted:",
        delete_data.get(
            "database_record_deleted"
        ),
    )
    print(
        "Audio file deleted:",
        delete_data.get(
            "audio_file_deleted"
        ),
    )
    print(
        "History final:",
        history_after_delete,
    )
    print(
        "Output exists:",
        output_path.exists(),
    )

    print("HTTP cleanup: PASSED")

finally:
    cleanup_errors: list[str] = []

    try:
        with sqlite3.connect(
            str(database_path),
            timeout=30,
        ) as connection:
            remaining_rows = (
                connection.execute(
                    """
                    SELECT
                        id,
                        output_filename
                    FROM generated_audio
                    WHERE text = ?
                    """,
                    (TEST_TEXT,),
                ).fetchall()
            )

            cleanup_filenames = {
                str(row[1])
                for row in remaining_rows
                if row[1]
            }

            if remaining_rows:
                connection.execute(
                    """
                    DELETE FROM generated_audio
                    WHERE text = ?
                    """,
                    (TEST_TEXT,),
                )

                connection.commit()

    except Exception as error:
        cleanup_filenames = set()

        cleanup_errors.append(
            "Emergency database cleanup failed: "
            f"{type(error).__name__}: {error}"
        )

    try:
        if output_path is not None:
            cleanup_filenames.add(
                output_path.name
            )

        for filename in cleanup_filenames:
            candidate = (
                output_folder
                / filename
            ).resolve()

            if (
                candidate.parent
                == output_folder
                and candidate.exists()
            ):
                candidate.unlink()

    except Exception as error:
        cleanup_errors.append(
            "Emergency output cleanup failed: "
            f"{type(error).__name__}: {error}"
        )

    if history_before is not None:
        history_final = count_history()

        print("\nFINAL CLEANUP CHECK")
        print("-" * 80)
        print("History before:", history_before)
        print("History final:", history_final)

        if history_final != history_before:
            cleanup_errors.append(
                "Final history count differs from the "
                "pre-test count."
            )

    if (
        output_path is not None
        and output_path.exists()
    ):
        cleanup_errors.append(
            "Test WAV remains after final cleanup."
        )

    if cleanup_errors:
        raise RuntimeError(
            " | ".join(cleanup_errors)
        )

print("\n" + "=" * 80)
print("ROUTING METADATA PERSISTENCE TEST: PASSED")
print("=" * 80)
