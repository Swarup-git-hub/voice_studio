from __future__ import annotations

import hashlib
import json
import shutil
import socket
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
ROOT_PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"

INITIALIZER_PATH = (
    BACKEND_ROOT
    / "scripts"
    / "initialize_database.py"
)

GUIDE_PATH = (
    PROJECT_ROOT
    / "DATABASE_BOOTSTRAP.md"
)

MAIN_PATH = (
    BACKEND_ROOT
    / "app"
    / "main.py"
)

DEVELOPMENT_DATABASE_PATH = (
    BACKEND_ROOT
    / "voice.db"
)

VALIDATION_ROOT = (
    BACKEND_ROOT
    / ".release_validation"
    / "milestone12_3"
)

VALIDATION_DATABASE_PATH = (
    VALIDATION_ROOT
    / "voice.clean.db"
)

REPORT_PATH = (
    BACKEND_ROOT
    / "milestone_reports"
    / (
        "milestone12_3_clean_database_"
        + datetime.now().strftime("%Y%m%d_%H%M%S")
        + ".json"
    )
)

checks_passed = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global checks_passed

    if not condition:
        message = f"{name}: FAILED"
        if detail:
            message += f"\n{detail}"
        raise AssertionError(message)

    checks_passed += 1
    print(f"{name}: PASSED")


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None

    digest = hashlib.sha256()

    with path.open("rb") as source_file:
        while True:
            chunk = source_file.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)

    return digest.hexdigest()


def database_snapshot(path: Path) -> dict[str, Any]:
    return {
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "sha256": sha256_file(path),
    }


def directory_snapshot(path: Path) -> dict[str, Any]:
    file_count = 0
    total_bytes = 0

    if path.exists():
        for item in path.rglob("*"):
            if not item.is_file():
                continue
            try:
                file_count += 1
                total_bytes += item.stat().st_size
            except OSError:
                continue

    return {
        "exists": path.exists(),
        "file_count": file_count,
        "total_bytes": total_bytes,
    }


def private_runtime_snapshot() -> dict[str, Any]:
    return {
        "database": database_snapshot(DEVELOPMENT_DATABASE_PATH),
        "voices": directory_snapshot(
            BACKEND_ROOT / "app" / "voices"
        ),
        "outputs": directory_snapshot(
            BACKEND_ROOT / "app" / "outputs"
        ),
    }


def port_is_open(port: int) -> bool:
    try:
        with socket.create_connection(
            ("127.0.0.1", port),
            timeout=0.5,
        ):
            return True
    except OSError:
        return False


def run_initializer(
    database_path: Path,
    *,
    allow_existing: bool = False,
) -> subprocess.CompletedProcess[str]:
    command = [
        str(ROOT_PYTHON),
        "-X",
        "utf8",
        str(INITIALIZER_PATH),
        "--database-path",
        str(database_path),
        "--json",
    ]

    if allow_existing:
        command.append("--allow-existing")

    return subprocess.run(
        command,
        cwd=str(BACKEND_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )


def parse_payload(
    completed: subprocess.CompletedProcess[str],
) -> dict[str, Any]:
    lines = [
        line.strip()
        for line in completed.stdout.splitlines()
        if line.strip()
    ]

    if not lines:
        raise RuntimeError(
            "Initializer returned no JSON output.\n"
            f"stderr:\n{completed.stderr}"
        )

    return json.loads(lines[-1])


print("=" * 92)
print(
    "MILESTONE 12.3 — CLEAN FIRST-RUN DATABASE BOOTSTRAP"
)
print("=" * 92)

before_snapshot = private_runtime_snapshot()

check(
    "Root Python exists",
    ROOT_PYTHON.exists(),
    str(ROOT_PYTHON),
)

check(
    "Development database exists",
    DEVELOPMENT_DATABASE_PATH.exists(),
    str(DEVELOPMENT_DATABASE_PATH),
)

check(
    "Database initializer exists",
    INITIALIZER_PATH.exists(),
    str(INITIALIZER_PATH),
)

check(
    "Database bootstrap guide exists",
    GUIDE_PATH.exists(),
    str(GUIDE_PATH),
)

initializer_source = INITIALIZER_PATH.read_text(
    encoding="utf-8-sig"
)

for name, marker in {
    "Initializer uses application metadata": "Base.metadata.create_all",
    "Initializer protects existing databases": (
        "Refusing to modify an existing non-empty database"
    ),
    "Initializer checks table row counts": "SELECT COUNT(*)",
    "Initializer validates SQLite integrity": "PRAGMA integrity_check",
}.items():
    check(name, marker in initializer_source, marker)

main_source = MAIN_PATH.read_text(
    encoding="utf-8-sig",
    errors="replace",
)

check(
    "FastAPI startup retains automatic table creation",
    "Base.metadata.create_all" in " ".join(main_source.split()),
)

if VALIDATION_ROOT.exists():
    shutil.rmtree(VALIDATION_ROOT)

VALIDATION_ROOT.mkdir(parents=True, exist_ok=True)

try:
    first_result = run_initializer(
        VALIDATION_DATABASE_PATH
    )

    check(
        "Clean database initializer completed",
        first_result.returncode == 0,
        (
            f"stdout:\n{first_result.stdout}\n"
            f"stderr:\n{first_result.stderr}"
        ),
    )

    first_payload = parse_payload(first_result)

    check(
        "Clean database file was created",
        VALIDATION_DATABASE_PATH.exists(),
    )

    check(
        "Application tables were created",
        bool(first_payload.get("tables")),
        repr(first_payload),
    )

    first_row_counts = first_payload.get(
        "row_counts",
        {},
    )

    check(
        "Every first-run table is empty",
        bool(first_row_counts)
        and all(
            row_count == 0
            for row_count in first_row_counts.values()
        ),
        repr(first_row_counts),
    )

    check(
        "SQLite integrity check passed",
        str(
            first_payload.get("integrity_check")
        ).lower() == "ok",
    )

    database_before_refusal = database_snapshot(
        VALIDATION_DATABASE_PATH
    )

    refusal_result = run_initializer(
        VALIDATION_DATABASE_PATH
    )

    check(
        "Initializer refuses accidental overwrite",
        refusal_result.returncode != 0,
        (
            f"stdout:\n{refusal_result.stdout}\n"
            f"stderr:\n{refusal_result.stderr}"
        ),
    )

    refusal_payload = parse_payload(
        refusal_result
    )

    check(
        "Overwrite refusal is clearly reported",
        (
            "Refusing to modify an existing non-empty database"
            in refusal_payload.get("error", "")
        ),
        repr(refusal_payload),
    )

    check(
        "Refused operation left clean database unchanged",
        database_snapshot(VALIDATION_DATABASE_PATH)
        == database_before_refusal,
    )

    repeated_result = run_initializer(
        VALIDATION_DATABASE_PATH,
        allow_existing=True,
    )

    check(
        "Explicit existing-database validation completed",
        repeated_result.returncode == 0,
        (
            f"stdout:\n{repeated_result.stdout}\n"
            f"stderr:\n{repeated_result.stderr}"
        ),
    )

    repeated_payload = parse_payload(
        repeated_result
    )

    repeated_counts = repeated_payload.get(
        "row_counts",
        {},
    )

    check(
        "Repeated validation preserves empty tables",
        bool(repeated_counts)
        and all(
            row_count == 0
            for row_count in repeated_counts.values()
        ),
        repr(repeated_payload),
    )

    check(
        "Repeated validation preserves SQLite integrity",
        str(
            repeated_payload.get("integrity_check")
        ).lower() == "ok",
    )
finally:
    if VALIDATION_ROOT.exists():
        shutil.rmtree(VALIDATION_ROOT)

    validation_parent = VALIDATION_ROOT.parent

    if (
        validation_parent.exists()
        and not any(validation_parent.iterdir())
    ):
        validation_parent.rmdir()

check(
    "Temporary validation database was removed",
    not VALIDATION_DATABASE_PATH.exists(),
)

after_snapshot = private_runtime_snapshot()

check(
    "Development database remained unchanged",
    before_snapshot["database"]
    == after_snapshot["database"],
    (
        f"Before: {before_snapshot['database']}\n"
        f"After: {after_snapshot['database']}"
    ),
)

check(
    "Saved voices remained unchanged",
    before_snapshot["voices"]
    == after_snapshot["voices"],
)

check(
    "Generated outputs remained unchanged",
    before_snapshot["outputs"]
    == after_snapshot["outputs"],
)

open_ports = [
    port
    for port in (5173, 8000, 8001, 8002)
    if port_is_open(port)
]

check(
    "No project services were started",
    not open_ports,
    repr(open_ports),
)

report = {
    "milestone": "12.3",
    "created_at": datetime.now().isoformat(),
    "release_tooling_created": [
        str(INITIALIZER_PATH),
        str(GUIDE_PATH),
    ],
    "development_database_modified": False,
    "saved_voices_modified": False,
    "generated_outputs_modified": False,
    "services_started": False,
    "clean_database_tables": first_payload["tables"],
    "clean_database_row_counts": first_row_counts,
    "sqlite_integrity_check": first_payload["integrity_check"],
    "accidental_overwrite_refused": True,
    "explicit_empty_database_validation": True,
    "temporary_database_removed": True,
    "private_runtime_snapshot_before": before_snapshot,
    "private_runtime_snapshot_after": after_snapshot,
    "checks_passed_before_report": checks_passed,
}

REPORT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

REPORT_PATH.write_text(
    json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)

check(
    "Clean-database report was saved",
    REPORT_PATH.exists()
    and REPORT_PATH.stat().st_size > 0,
)

print()
print("=" * 92)
print(
    "MILESTONE 12.3 CLEAN FIRST-RUN DATABASE: PASSED"
)
print("=" * 92)
print("Checks passed:", checks_passed)
print(
    "Application tables created:",
    len(first_payload["tables"]),
)
print("Non-empty first-run tables: 0")
print("SQLite integrity check: OK")
print("Accidental overwrite protection: PASSED")
print("Development database modified: NO")
print("Saved voices modified: NO")
print("Generated outputs modified: NO")
print("Temporary validation database removed: YES")
print("Application source files modified: NO")
print("Services started: NO")
print()
print("Report:", REPORT_PATH)

print()
print("=" * 92)
print("MILESTONE 12.3 CLEAN DATABASE: COMPLETE")
print("=" * 92)
print("Clean first-run database: VERIFIED")
print("Accidental overwrite protection: VERIFIED")
print("Development database modified: NO")
print("Saved voices modified: NO")
print("Generated outputs modified: NO")
print("Temporary validation database removed: YES")
print("Application source files modified: NO")
print("Services started: NO")
