from __future__ import annotations

import sqlite3
import uuid
import wave
from pathlib import Path
from typing import Any

import requests


BASE_URL = "http://127.0.0.1:8000"
INDICF5_URL = "http://127.0.0.1:8002"
VOICE_ID = 10

BACKEND_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

DATABASE_PATH = BACKEND_ROOT / "voice.db"

OUTPUT_DIRECTORY = (
    BACKEND_ROOT
    / "app"
    / "outputs"
).resolve()

TEST_MARKER = (
    "M1055-"
    + uuid.uuid4().hex[:10].upper()
)

SOURCE_TEXT = (
    '  “Browser”లో   URL   API!!!!'
    '\u200b  ఇది HTTP పరీక్ష.  '
    + TEST_MARKER
    + "  "
)

EXPECTED_HISTORY_TEXT = (
    '"Browser"లో URL API! '
    'ఇది HTTP పరీక్ష. '
    + TEST_MARKER
)

checks_passed = 0


def check(
    name: str,
    condition: bool,
    detail: str = "",
) -> None:
    global checks_passed

    if not condition:
        raise AssertionError(
            f"{name}: FAILED"
            + (
                f"\n{detail}"
                if detail
                else ""
            )
        )

    checks_passed += 1

    print(
        f"{name}: PASSED"
    )


def request_json(
    method: str,
    url: str,
    *,
    timeout: tuple[int, int] = (10, 900),
    **kwargs: Any,
) -> tuple[requests.Response, Any]:
    response = requests.request(
        method,
        url,
        timeout=timeout,
        **kwargs,
    )

    try:
        body = response.json()
    except ValueError:
        body = {
            "raw_body": response.text,
        }

    return response, body


def connect_database() -> sqlite3.Connection:
    connection = sqlite3.connect(
        str(DATABASE_PATH),
        timeout=30,
    )

    connection.row_factory = sqlite3.Row

    return connection


def database_integrity() -> str:
    with connect_database() as connection:
        return str(
            connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]
        )


def history_ids() -> list[int]:
    with connect_database() as connection:
        return [
            int(row[0])
            for row in connection.execute(
                """
                SELECT id
                FROM generated_audio
                ORDER BY id
                """
            ).fetchall()
        ]


def history_count() -> int:
    return len(
        history_ids()
    )


def output_files() -> set[str]:
    if not OUTPUT_DIRECTORY.exists():
        return set()

    return {
        path.name
        for path in OUTPUT_DIRECTORY.glob(
            "*.wav"
        )
    }


def database_row(
    generation_id: int,
) -> sqlite3.Row | None:
    with connect_database() as connection:
        return connection.execute(
            """
            SELECT
                id,
                voice_id,
                text,
                output_filename,
                engine_requested,
                engine_used,
                fallback_used,
                routing_reason
            FROM generated_audio
            WHERE id = ?
            """,
            (
                generation_id,
            ),
        ).fetchone()


def marker_rows() -> list[sqlite3.Row]:
    with connect_database() as connection:
        return connection.execute(
            """
            SELECT
                id,
                output_filename
            FROM generated_audio
            WHERE text LIKE ?
            """,
            (
                f"%{TEST_MARKER}%",
            ),
        ).fetchall()


def validate_wav(
    wav_path: Path,
) -> None:
    check(
        "Generated WAV exists",
        wav_path.exists(),
        str(wav_path),
    )

    check(
        "Generated WAV is non-empty",
        wav_path.stat().st_size > 44,
        f"Bytes={wav_path.stat().st_size}",
    )

    with wave.open(
        str(wav_path),
        "rb",
    ) as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()

    duration = (
        frame_count / sample_rate
        if sample_rate
        else 0.0
    )

    check(
        "Generated WAV is mono",
        channels == 1,
        f"Channels={channels}",
    )

    check(
        "Generated WAV is 24 kHz",
        sample_rate == 24_000,
        f"Sample rate={sample_rate}",
    )

    check(
        "Generated WAV is PCM16",
        sample_width == 2,
        f"Sample width={sample_width}",
    )

    check(
        "Generated WAV has positive duration",
        duration > 0,
        f"Duration={duration}",
    )

    print(
        "Generated duration:",
        round(duration, 3),
        "seconds",
    )


def cleanup_marker_rows() -> None:
    rows = marker_rows()

    for row in rows:
        generation_id = int(
            row["id"]
        )

        try:
            response = requests.delete(
                (
                    f"{BASE_URL}/speech/history/"
                    f"{generation_id}"
                ),
                timeout=(5, 60),
            )

            print(
                "Emergency cleanup:",
                generation_id,
                response.status_code,
            )

        except Exception as error:
            print(
                "Emergency cleanup warning:",
                generation_id,
                error,
            )


print("=" * 88)
print("MILESTONE 10.5 LIVE PREPROCESSING HTTP REGRESSION")
print("=" * 88)
print("Database:", DATABASE_PATH)
print("Output directory:", OUTPUT_DIRECTORY)
print("Test marker:", TEST_MARKER)
print("Expected history text:", EXPECTED_HISTORY_TEXT)
print()

check(
    "Active database exists",
    DATABASE_PATH.exists(),
    str(DATABASE_PATH),
)

check(
    "Initial database integrity",
    database_integrity() == "ok",
    database_integrity(),
)

baseline_ids = history_ids()
baseline_count = len(
    baseline_ids
)
baseline_outputs = output_files()

print(
    "History rows before:",
    baseline_count,
)

try:
    backend_response, backend_body = request_json(
        "GET",
        f"{BASE_URL}/health",
        timeout=(5, 30),
    )

    check(
        "Main backend health",
        backend_response.status_code == 200,
        repr(backend_body),
    )

    indic_response, indic_body = request_json(
        "GET",
        f"{INDICF5_URL}/health",
        timeout=(5, 60),
    )

    check(
        "IndicF5 model health",
        (
            indic_response.status_code == 200
            and indic_body.get(
                "model_loaded"
            )
            is True
        ),
        repr(indic_body),
    )

    generation_response, generation_body = (
        request_json(
            "POST",
            f"{BASE_URL}/speech/generate",
            json={
                "voice_id": VOICE_ID,
                "text": SOURCE_TEXT,
                "speed": 1.0,
                "volume": 1.0,
                "bass": 0.0,
                "engine": "indicf5",
                "allow_fallback": False,
            },
        )
    )

    check(
        "Live IndicF5 generation",
        generation_response.status_code
        == 200,
        (
            f"Status={generation_response.status_code}; "
            f"Body={generation_body}"
        ),
    )

    check(
        "Generation response is JSON",
        isinstance(
            generation_body,
            dict,
        ),
        repr(generation_body),
    )

    generation_id = int(
        generation_body["id"]
    )

    output_filename = str(
        generation_body[
            "output_filename"
        ]
    )

    output_path = (
        OUTPUT_DIRECTORY
        / output_filename
    ).resolve()

    check(
        "History gained exactly one row",
        history_count()
        == baseline_count + 1,
        (
            f"Before={baseline_count}; "
            f"After={history_count()}"
        ),
    )

    check(
        "Response contains readable normalised text",
        generation_body.get("text")
        == EXPECTED_HISTORY_TEXT,
        (
            f"Expected={EXPECTED_HISTORY_TEXT!r}; "
            f"Actual={generation_body.get('text')!r}"
        ),
    )

    check(
        "Explicit IndicF5 metadata",
        (
            generation_body.get(
                "engine_requested"
            )
            == "indicf5"
            and generation_body.get(
                "engine_used"
            )
            == "indicf5"
        ),
        repr(generation_body),
    )

    check(
        "Mixed-language detection preserved",
        generation_body.get(
            "detected_language"
        )
        == "mixed",
        repr(
            generation_body.get(
                "detected_language"
            )
        ),
    )

    check(
        "Fallback was not used",
        generation_body.get(
            "fallback_used"
        )
        is False,
        repr(
            generation_body.get(
                "fallback_used"
            )
        ),
    )

    check(
        "Explicit routing reason preserved",
        generation_body.get(
            "routing_reason"
        )
        == "explicit_indicf5",
        repr(
            generation_body.get(
                "routing_reason"
            )
        ),
    )

    row = database_row(
        generation_id
    )

    check(
        "Generated SQLite row exists",
        row is not None,
    )

    check(
        "SQLite stores readable normalised text",
        (
            row is not None
            and row["text"]
            == EXPECTED_HISTORY_TEXT
        ),
        (
            repr(row["text"])
            if row is not None
            else "Missing row"
        ),
    )

    check(
        "SQLite stores routing metadata",
        (
            row is not None
            and row["engine_requested"]
            == "indicf5"
            and row["engine_used"]
            == "indicf5"
            and bool(
                row["fallback_used"]
            )
            is False
            and row["routing_reason"]
            == "explicit_indicf5"
        ),
    )

    history_response, history_body = (
        request_json(
            "GET",
            (
                f"{BASE_URL}/speech/history/"
                f"{generation_id}"
            ),
            timeout=(5, 30),
        )
    )

    check(
        "History item is retrievable",
        history_response.status_code
        == 200,
        repr(history_body),
    )

    check(
        "History API returns readable text",
        history_body.get("text")
        == EXPECTED_HISTORY_TEXT,
        repr(
            history_body.get("text")
        ),
    )

    check(
        "History API returns routing metadata",
        (
            history_body.get(
                "engine_requested"
            )
            == "indicf5"
            and history_body.get(
                "engine_used"
            )
            == "indicf5"
            and history_body.get(
                "fallback_used"
            )
            is False
            and history_body.get(
                "routing_reason"
            )
            == "explicit_indicf5"
        ),
        repr(history_body),
    )

    validate_wav(
        output_path
    )

    delete_response, delete_body = (
        request_json(
            "DELETE",
            (
                f"{BASE_URL}/speech/history/"
                f"{generation_id}"
            ),
            timeout=(5, 60),
        )
    )

    check(
        "Delete endpoint succeeded",
        delete_response.status_code
        == 200,
        repr(delete_body),
    )

    check(
        "Delete confirmed database removal",
        delete_body.get(
            "database_record_deleted"
        )
        is True,
        repr(delete_body),
    )

    check(
        "Generated SQLite row removed",
        database_row(
            generation_id
        )
        is None,
    )

    check(
        "Generated WAV removed",
        not output_path.exists(),
        str(output_path),
    )

    check(
        "History restored after deletion",
        history_ids()
        == baseline_ids,
    )

    check(
        "Output directory restored after deletion",
        output_files()
        == baseline_outputs,
    )

    over_limit_ids = history_ids()
    over_limit_outputs = output_files()

    over_limit_response, over_limit_body = (
        request_json(
            "POST",
            f"{BASE_URL}/speech/generate",
            json={
                "voice_id": VOICE_ID,
                "text": "a" * 1501,
                "speed": 1.0,
                "volume": 1.0,
                "bass": 0.0,
                "engine": "indicf5",
                "allow_fallback": False,
            },
            timeout=(5, 60),
        )
    )

    check(
        "1,501-character request receives HTTP 400",
        over_limit_response.status_code
        == 400,
        (
            f"Status={over_limit_response.status_code}; "
            f"Body={over_limit_body}"
        ),
    )

    over_limit_detail = str(
        over_limit_body.get(
            "detail",
            over_limit_body,
        )
    )

    check(
        "Over-limit error states the 1,500 boundary",
        "1500" in over_limit_detail,
        over_limit_detail,
    )

    check(
        "Over-limit request creates no history",
        history_ids()
        == over_limit_ids,
    )

    check(
        "Over-limit request creates no output WAV",
        output_files()
        == over_limit_outputs,
    )

    invisible_ids = history_ids()
    invisible_outputs = output_files()

    invisible_response, invisible_body = (
        request_json(
            "POST",
            f"{BASE_URL}/speech/generate",
            json={
                "voice_id": VOICE_ID,
                "text": (
                    "\ufeff"
                    "\u200b"
                    "\u2060"
                ),
                "speed": 1.0,
                "volume": 1.0,
                "bass": 0.0,
                "engine": "indicf5",
                "allow_fallback": False,
            },
            timeout=(5, 60),
        )
    )

    check(
        "Invisible-only request receives HTTP 400",
        invisible_response.status_code
        == 400,
        (
            f"Status={invisible_response.status_code}; "
            f"Body={invisible_body}"
        ),
    )

    invisible_detail = str(
        invisible_body.get(
            "detail",
            invisible_body,
        )
    ).lower()

    check(
        "Invisible-only error explains empty preprocessed text",
        (
            "empty" in invisible_detail
            and "preprocess" in invisible_detail
        ),
        invisible_detail,
    )

    check(
        "Invisible-only request creates no history",
        history_ids()
        == invisible_ids,
    )

    check(
        "Invisible-only request creates no output WAV",
        output_files()
        == invisible_outputs,
    )

    check(
        "Final database integrity",
        database_integrity() == "ok",
        database_integrity(),
    )

    check(
        "Final history IDs equal baseline",
        history_ids()
        == baseline_ids,
    )

    check(
        "Final output files equal baseline",
        output_files()
        == baseline_outputs,
    )

    check(
        "No marked test record remains",
        len(marker_rows()) == 0,
    )

finally:
    cleanup_marker_rows()

print()
print("=" * 88)
print(
    "MILESTONE 10.5 LIVE PREPROCESSING HTTP REGRESSION: PASSED"
)
print("=" * 88)
print(
    "Checks passed:",
    checks_passed,
)
print(
    "History before:",
    baseline_count,
)
print(
    "History after :",
    history_count(),
)
