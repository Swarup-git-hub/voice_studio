from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
FRONTEND_ROOT = PROJECT_ROOT / "frontend"

REPORT_FOLDER = (
    BACKEND_ROOT
    / "milestone_reports"
)

TIMESTAMP = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

REPORT_PATH = (
    REPORT_FOLDER
    / f"milestone11_1a_reliability_startup_audit_{TIMESTAMP}.txt"
)

report_lines: list[str] = []


def add_line(
    text: str = "",
) -> None:
    report_lines.append(
        text
    )

    print(
        text
    )


def add_section(
    title: str,
) -> None:
    add_line()
    add_line("=" * 92)
    add_line(title)
    add_line("=" * 92)


def test_tcp_port(
    *,
    name: str,
    host: str,
    port: int,
) -> bool:
    try:
        with socket.create_connection(
            (
                host,
                port,
            ),
            timeout=3.0,
        ):
            pass

        add_line(
            f"{name} TCP {port}: LISTENING"
        )

        return True

    except OSError as error:
        add_line(
            f"{name} TCP {port}: FAILED - {error}"
        )

        return False


def test_http_endpoint(
    *,
    name: str,
    url: str,
) -> bool:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "AI-Voice-Studio-Milestone-11-Audit"
            ),
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=20,
        ) as response:
            status = int(
                response.getcode()
                or 200
            )

            content_bytes = response.read(
                601
            )

            charset = (
                response.headers.get_content_charset()
                or "utf-8"
            )

            content = content_bytes.decode(
                charset,
                errors="replace",
            )

            if len(
                content
            ) > 600:
                content = (
                    content[:600]
                    + "..."
                )

            add_line(
                f"{name} HTTP status: {status}"
            )

            add_line(
                f"{name} response: {content}"
            )

            return (
                200
                <= status
                < 400
            )

    except urllib.error.HTTPError as error:
        status = int(
            error.code
        )

        try:
            content = error.read(
                600
            ).decode(
                "utf-8",
                errors="replace",
            )

        except Exception:
            content = ""

        add_line(
            f"{name} HTTP status: {status}"
        )

        add_line(
            f"{name} response: {content}"
        )

        return False

    except Exception as error:
        add_line(
            f"{name} HTTP probe: FAILED - {error}"
        )

        return False


def add_source_markers(
    *,
    title: str,
    path: Path,
    patterns: list[str],
) -> None:
    add_section(
        title
    )

    if not (
        path.exists()
        and path.is_file()
    ):
        add_line(
            f"FILE MISSING: {path}"
        )

        return

    add_line(
        f"File: {path}"
    )

    add_line(
        f"Size: {path.stat().st_size} bytes"
    )

    source = path.read_text(
        encoding="utf-8-sig",
        errors="replace",
    )

    lowercase_patterns = [
        pattern.lower()
        for pattern in patterns
    ]

    matches: list[
        tuple[
            int,
            str,
        ]
    ] = []

    for line_number, line in enumerate(
        source.splitlines(),
        start=1,
    ):
        lowercase_line = line.lower()

        if any(
            pattern
            in lowercase_line
            for pattern
            in lowercase_patterns
        ):
            matches.append(
                (
                    line_number,
                    line.strip(),
                )
            )

    if not matches:
        add_line(
            "No requested markers found."
        )

        return

    for line_number, line in matches:
        add_line(
            f"{line_number:5}: {line}"
        )


add_line("=" * 92)
add_line(
    "MILESTONE 11.1A - RELIABILITY AND STARTUP BASELINE AUDIT"
)
add_line("=" * 92)

add_line(
    "Created: "
    + datetime.now().isoformat(
        timespec="seconds"
    )
)

add_line(
    f"Project root: {PROJECT_ROOT}"
)

add_line(
    f"Backend root: {BACKEND_ROOT}"
)

add_line(
    f"Frontend root: {FRONTEND_ROOT}"
)


# ============================================================
# Service ports
# ============================================================

add_section(
    "SERVICE PORTS"
)

frontend_tcp = test_tcp_port(
    name="Frontend",
    host="127.0.0.1",
    port=5173,
)

backend_tcp = test_tcp_port(
    name="FastAPI backend",
    host="127.0.0.1",
    port=8000,
)

cosyvoice_tcp = test_tcp_port(
    name="CosyVoice",
    host="127.0.0.1",
    port=8001,
)

indicf5_tcp = test_tcp_port(
    name="IndicF5",
    host="127.0.0.1",
    port=8002,
)


# ============================================================
# HTTP health
# ============================================================

add_section(
    "HTTP HEALTH"
)

frontend_http = test_http_endpoint(
    name="Frontend",
    url="http://127.0.0.1:5173",
)

backend_http = test_http_endpoint(
    name="FastAPI backend",
    url="http://127.0.0.1:8000/health",
)

cosyvoice_http = test_http_endpoint(
    name="CosyVoice",
    url="http://127.0.0.1:8001/health",
)

indicf5_http = test_http_endpoint(
    name="IndicF5",
    url="http://127.0.0.1:8002/health",
)


# ============================================================
# Startup files
# ============================================================

add_section(
    "CURRENT STARTUP FILES"
)

startup_extensions = {
    ".ps1",
    ".bat",
    ".cmd",
}

startup_files: set[
    Path
] = set()

for search_root in (
    PROJECT_ROOT,
    BACKEND_ROOT,
    FRONTEND_ROOT,
):
    if not search_root.exists():
        continue

    for candidate in search_root.iterdir():
        if (
            candidate.is_file()
            and candidate.suffix.lower()
            in startup_extensions
        ):
            startup_files.add(
                candidate.resolve()
            )

if not startup_files:
    add_line(
        "No root-level PowerShell, BAT or CMD startup files were found."
    )

else:
    for startup_file in sorted(
        startup_files,
        key=lambda item: str(
            item
        ).lower(),
    ):
        add_line(
            str(
                startup_file
            )
        )


# ============================================================
# Frontend package scripts
# ============================================================

add_section(
    "FRONTEND PACKAGE SCRIPTS"
)

package_path = (
    FRONTEND_ROOT
    / "package.json"
)

if package_path.exists():
    package_data = json.loads(
        package_path.read_text(
            encoding="utf-8-sig",
        )
    )

    package_scripts = package_data.get(
        "scripts"
    )

    if isinstance(
        package_scripts,
        dict,
    ):
        for script_name, command in (
            package_scripts.items()
        ):
            add_line(
                f"{script_name} = {command}"
            )

    else:
        add_line(
            "No package scripts were found."
        )

else:
    add_line(
        "package.json was not found."
    )


# ============================================================
# Backend markers
# ============================================================

add_source_markers(
    title="BACKEND MAIN APPLICATION MARKERS",
    path=(
        BACKEND_ROOT
        / "app"
        / "main.py"
    ),
    patterns=[
        "FastAPI(",
        "CORSMiddleware",
        "add_middleware",
        "include_router",
        "exception_handler",
        "startup",
        "shutdown",
        "/health",
        "health",
    ],
)

add_source_markers(
    title="SPEECH API ERROR AND TRANSACTION MARKERS",
    path=(
        BACKEND_ROOT
        / "app"
        / "api"
        / "speech.py"
    ),
    patterns=[
        "HTTPException",
        "EngineUnavailableError",
        "EngineGenerationError",
        "status_code",
        "timeout",
        "delete_pending",
        "FileResponse",
    ],
)

add_source_markers(
    title="TTS SERVICE RELIABILITY MARKERS",
    path=(
        BACKEND_ROOT
        / "app"
        / "services"
        / "tts_service.py"
    ),
    patterns=[
        "try:",
        "except",
        "finally:",
        "db.rollback",
        "db.commit",
        "delete_file_safely",
        "delete_pending",
        "apply_audio_controls",
        "segmented_synthesis.generate",
    ],
)


# ============================================================
# Frontend markers
# ============================================================

add_source_markers(
    title="FRONTEND LOADING AND ERROR MARKERS",
    path=(
        FRONTEND_ROOT
        / "src"
        / "App.jsx"
    ),
    patterns=[
        "initialLoading",
        "generating",
        "deletingId",
        "setError",
        "setNotice",
        "disabled=",
        "Loading",
        "Generating",
        "progress",
    ],
)

add_source_markers(
    title="FRONTEND API CLIENT MARKERS",
    path=(
        FRONTEND_ROOT
        / "src"
        / "api.js"
    ),
    patterns=[
        "fetch(",
        "AbortController",
        "timeout",
        "response.ok",
        "throw new Error",
        "127.0.0.1:8000",
    ],
)


# ============================================================
# Summary
# ============================================================

add_section(
    "BASELINE SUMMARY"
)

service_results = [
    (
        "Frontend TCP",
        frontend_tcp,
    ),
    (
        "Backend TCP",
        backend_tcp,
    ),
    (
        "CosyVoice TCP",
        cosyvoice_tcp,
    ),
    (
        "IndicF5 TCP",
        indicf5_tcp,
    ),
    (
        "Frontend HTTP",
        frontend_http,
    ),
    (
        "Backend HTTP",
        backend_http,
    ),
    (
        "CosyVoice HTTP",
        cosyvoice_http,
    ),
    (
        "IndicF5 HTTP",
        indicf5_http,
    ),
]

for result_name, result_value in (
    service_results
):
    add_line(
        f"{result_name} = {result_value}"
    )

healthy_result_count = sum(
    1
    for _name, result
    in service_results
    if result
)

add_line()

add_line(
    "Healthy checks: "
    f"{healthy_result_count} / "
    f"{len(service_results)}"
)

add_line()

add_line(
    "Audit mode: READ-ONLY"
)

add_line(
    "Application files modified: NO"
)

add_line()

add_line("=" * 92)

add_line(
    "MILESTONE 11.1A RELIABILITY AND STARTUP BASELINE AUDIT: COMPLETE"
)

add_line("=" * 92)

REPORT_FOLDER.mkdir(
    parents=True,
    exist_ok=True,
)

REPORT_PATH.write_text(
    "\n".join(
        report_lines
    )
    + "\n",
    encoding="utf-8",
)

print()
print(
    "Audit report:"
)

print(
    REPORT_PATH
)
