from __future__ import annotations

import json
import socket
from pathlib import Path
from typing import Any

import requests

from app.core.config import settings
from app.database.connection import SessionLocal
from app.database.models import GeneratedAudio


BASE_URL = "http://127.0.0.1:8000"
VOICE_ID = 10

TEST_TEXT = (
    "This request must fail because both "
    "speech engines are unavailable."
)


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise RuntimeError(message)


def port_is_open(
    port: int,
) -> bool:
    with socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    ) as connection:
        connection.settimeout(1.0)

        return (
            connection.connect_ex(
                ("127.0.0.1", port)
            )
            == 0
        )


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
output_files_before: set[str] = set()

try:
    require(
        port_is_open(8000),
        "Main backend is not running on port 8000.",
    )

    require(
        not port_is_open(8001),
        "CosyVoice must be stopped on port 8001.",
    )

    require(
        not port_is_open(8002),
        "IndicF5 must be stopped on port 8002.",
    )

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
        "engine": "auto",
        "allow_fallback": True,
    }

    print("=" * 80)
    print("ALL ENGINES UNAVAILABLE HTTP TEST")
    print("=" * 80)

    print("Main backend open:", port_is_open(8000))
    print("CosyVoice open:", port_is_open(8001))
    print("IndicF5 open:", port_is_open(8002))
    print("History before:", history_before)

    print("\nREQUEST")
    print("-" * 80)
    display_json(payload)

    response = requests.post(
        f"{BASE_URL}/speech/generate",
        json=payload,
        timeout=(10, 120),
    )

    print("\nHTTP RESPONSE")
    print("-" * 80)
    print("Status code:", response.status_code)

    try:
        response_data = response.json()
    except ValueError:
        response_data = {
            "raw_body": response.text,
        }

    display_json(response_data)

    database.expire_all()

    history_after = (
        database.query(GeneratedAudio).count()
    )

    matching_rows = (
        database.query(GeneratedAudio)
        .filter(
            GeneratedAudio.text
            == TEST_TEXT
        )
        .all()
    )

    output_files_after = {
        file.name
        for file in output_folder.iterdir()
        if file.is_file()
    }

    unexpected_files = (
        output_files_after
        - output_files_before
    )

    detail = ""

    if isinstance(response_data, dict):
        detail = str(
            response_data.get(
                "detail",
                "",
            )
        )

    print("\nFAILURE VALIDATION")
    print("-" * 80)
    print("Response detail:", detail)
    print("History after:", history_after)
    print("Matching rows:", len(matching_rows))
    print(
        "Unexpected output files:",
        sorted(unexpected_files),
    )

    checks = {
        "Controlled HTTP 503": (
            response.status_code == 503
        ),
        "Error detail returned": (
            bool(detail.strip())
        ),
        "Both engines mentioned": (
            "CosyVoice" in detail
            and "IndicF5" in detail
        ),
        "History unchanged": (
            history_after == history_before
        ),
        "No matching history row": (
            len(matching_rows) == 0
        ),
        "No output file created": (
            not unexpected_files
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
            "Unavailable-engine checks failed: "
            + ", ".join(failed_checks)
        )

    print("\n" + "=" * 80)
    print("ALL ENGINES UNAVAILABLE RESPONSE: PASSED")
    print("=" * 80)

finally:
    cleanup_errors: list[str] = []

    try:
        database.rollback()

        unexpected_rows = (
            database.query(GeneratedAudio)
            .filter(
                GeneratedAudio.text
                == TEST_TEXT
            )
            .all()
        )

        cleanup_filenames = {
            row.output_filename
            for row in unexpected_rows
            if row.output_filename
        }

        for row in unexpected_rows:
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

    output_files_final = {
        file.name
        for file in Path(
            settings.OUTPUT_FOLDER
        ).resolve().iterdir()
        if file.is_file()
    }

    remaining_new_files = (
        output_files_final
        - output_files_before
    )

    print("\nCLEANUP")
    print("-" * 80)
    print("History final:", history_final)
    print(
        "Unexpected new output files:",
        sorted(remaining_new_files),
    )

    if (
        history_before is not None
        and history_final != history_before
    ):
        cleanup_errors.append(
            "History count was not restored."
        )

    if remaining_new_files:
        cleanup_errors.append(
            "Unexpected output files remain."
        )

    database.close()

    if cleanup_errors:
        raise RuntimeError(
            " | ".join(cleanup_errors)
        )

    print("Failure test cleanup: PASSED")

print("\n" + "=" * 80)
print("ALL ENGINES UNAVAILABLE HTTP TEST: PASSED")
print("=" * 80)
