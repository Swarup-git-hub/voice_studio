from __future__ import annotations

import sqlite3
from pathlib import Path

from app.database.models import GeneratedAudio
from app.database.schemas import GeneratedAudioResponse


backend_root = Path.cwd().resolve()
database_path = backend_root / "voice.db"

required_columns = {
    "engine_requested",
    "engine_used",
    "fallback_used",
    "routing_reason",
}

if not database_path.exists():
    raise FileNotFoundError(
        f"Database not found: {database_path}"
    )

with sqlite3.connect(
    str(database_path),
    timeout=30,
) as connection:
    integrity = connection.execute(
        "PRAGMA integrity_check"
    ).fetchone()[0]

    columns = {
        row[1]
        for row in connection.execute(
            "PRAGMA table_info(generated_audio)"
        ).fetchall()
    }

    history_count = int(
        connection.execute(
            """
            SELECT COUNT(*)
            FROM generated_audio
            """
        ).fetchone()[0]
    )

    legacy_count = int(
        connection.execute(
            """
            SELECT COUNT(*)
            FROM generated_audio
            WHERE
                engine_requested = 'legacy'
                AND engine_used = 'legacy'
                AND fallback_used = 0
                AND routing_reason = 'legacy_record'
            """
        ).fetchone()[0]
    )

    null_metadata_count = int(
        connection.execute(
            """
            SELECT COUNT(*)
            FROM generated_audio
            WHERE
                engine_requested IS NULL
                OR engine_used IS NULL
                OR fallback_used IS NULL
                OR routing_reason IS NULL
            """
        ).fetchone()[0]
    )

    inconsistent_legacy_count = int(
        connection.execute(
            """
            SELECT COUNT(*)
            FROM generated_audio
            WHERE
                (
                    engine_requested = 'legacy'
                    OR engine_used = 'legacy'
                    OR routing_reason = 'legacy_record'
                )
                AND NOT (
                    engine_requested = 'legacy'
                    AND engine_used = 'legacy'
                    AND fallback_used = 0
                    AND routing_reason = 'legacy_record'
                )
            """
        ).fetchone()[0]
    )

routed_count = history_count - legacy_count

checks = {
    "Database integrity": integrity == "ok",
    "All routing columns exist": (
        required_columns <= columns
    ),
    "Metadata contains no NULL values": (
        null_metadata_count == 0
    ),
    "Legacy metadata is internally consistent": (
        inconsistent_legacy_count == 0
    ),
    "Legacy rows are a valid subset": (
        0 <= legacy_count <= history_count
    ),
    "ORM routing fields exist": all(
        hasattr(GeneratedAudio, field)
        for field in required_columns
    ),
    "Response routing fields exist": all(
        field in GeneratedAudioResponse.model_fields
        for field in required_columns
    ),
}

print("=" * 80)
print("ROUTING METADATA MIGRATION VERIFICATION")
print("=" * 80)
print("Database:", database_path)
print("History count:", history_count)
print("Legacy count:", legacy_count)
print("Routed count:", routed_count)
print("NULL metadata rows:", null_metadata_count)
print(
    "Inconsistent legacy rows:",
    inconsistent_legacy_count,
)
print("Columns:", sorted(columns))
print()

failed_checks: list[str] = []

for name, passed in checks.items():
    print(
        f"{name}:",
        "PASSED" if passed else "FAILED",
    )

    if not passed:
        failed_checks.append(name)

if failed_checks:
    raise RuntimeError(
        "Verification failed: "
        + ", ".join(failed_checks)
    )

print("=" * 80)
print(
    "ROUTING METADATA MIGRATION VERIFICATION: PASSED"
)
print("=" * 80)
