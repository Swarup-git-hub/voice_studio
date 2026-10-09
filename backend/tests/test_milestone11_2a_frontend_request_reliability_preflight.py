from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
FRONTEND_ROOT = PROJECT_ROOT / "frontend"

API_PATH = (
    FRONTEND_ROOT
    / "src"
    / "api.js"
)

APP_PATH = (
    FRONTEND_ROOT
    / "src"
    / "App.jsx"
)

SPEECH_PATH = (
    BACKEND_ROOT
    / "app"
    / "api"
    / "speech.py"
)

REPORT_PATH = (
    BACKEND_ROOT
    / "milestone_reports"
    / "milestone11_2a_frontend_request_reliability_preflight.json"
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


def matching_lines(
    source: str,
    patterns: list[str],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    lowered_patterns = [
        pattern.lower()
        for pattern in patterns
    ]

    for line_number, line in enumerate(
        source.splitlines(),
        start=1,
    ):
        lowered_line = line.lower()

        matched_patterns = [
            patterns[index]
            for index, lowered_pattern
            in enumerate(
                lowered_patterns
            )
            if lowered_pattern in lowered_line
        ]

        if matched_patterns:
            results.append(
                {
                    "line": line_number,
                    "text": line.rstrip(),
                    "patterns": matched_patterns,
                }
            )

    return results


def source_excerpt(
    source: str,
    start_line: int,
    end_line: int,
) -> str:
    lines = source.splitlines()

    safe_start = max(
        1,
        start_line,
    )

    safe_end = min(
        len(
            lines
        ),
        end_line,
    )

    return "\n".join(
        f"{line_number:5}: {lines[line_number - 1]}"
        for line_number in range(
            safe_start,
            safe_end + 1,
        )
    )


def print_matches(
    title: str,
    matches: list[dict[str, Any]],
) -> None:
    print()
    print("=" * 92)
    print(title)
    print("=" * 92)

    if not matches:
        print("No matching markers found.")
        return

    for match in matches:
        print(
            f"{match['line']:5}: "
            f"{match['text'].strip()}"
        )


print("=" * 92)
print(
    "MILESTONE 11.2A — FRONTEND REQUEST "
    "RELIABILITY PREFLIGHT"
)
print("=" * 92)

check(
    "Frontend API client exists",
    API_PATH.exists(),
    str(
        API_PATH
    ),
)

check(
    "Frontend application exists",
    APP_PATH.exists(),
    str(
        APP_PATH
    ),
)

check(
    "Speech API module exists",
    SPEECH_PATH.exists(),
    str(
        SPEECH_PATH
    ),
)

api_source = API_PATH.read_text(
    encoding="utf-8-sig",
)

app_source = APP_PATH.read_text(
    encoding="utf-8-sig",
)

speech_source = SPEECH_PATH.read_text(
    encoding="utf-8-sig",
)

fetch_matches = matching_lines(
    api_source,
    [
        "fetch(",
    ],
)

api_error_matches = matching_lines(
    api_source,
    [
        "response.ok",
        "throw new Error",
        "response.json",
        "response.text",
        "try {",
        "catch",
    ],
)

timeout_matches = matching_lines(
    api_source,
    [
        "AbortController",
        "AbortSignal",
        "signal:",
        "setTimeout",
        "clearTimeout",
        "timeout",
        "DOMException",
        "AbortError",
    ],
)

app_state_matches = matching_lines(
    app_source,
    [
        "generating",
        "setGenerating",
        "setError",
        "setNotice",
        "disabled=",
        "handleGenerate",
        "generateSpeech",
    ],
)

backend_error_matches = matching_lines(
    speech_source,
    [
        "EngineUnavailableError",
        "EngineGenerationError",
        "status_code=503",
        "status_code=502",
        "status_code=500",
        "HTTPException",
    ],
)

check(
    "Frontend API client performs HTTP fetch requests",
    bool(
        fetch_matches
    ),
)

check(
    "Frontend API client checks response success",
    "response.ok"
    in api_source,
)

check(
    "Frontend API client raises readable errors",
    "throw new Error"
    in api_source,
)

check(
    "Frontend application tracks generation state",
    (
        "generating"
        in app_source
        and "setGenerating"
        in app_source
    ),
)

check(
    "Frontend application exposes generation errors",
    "setError"
    in app_source,
)

check(
    "Backend exposes engine-unavailable handling",
    (
        "EngineUnavailableError"
        in speech_source
        and "status_code=503"
        in speech_source
    ),
)

check(
    "Backend exposes generation-error handling",
    (
        "EngineGenerationError"
        in speech_source
        and "status_code=502"
        in speech_source
    ),
)

fetch_line_numbers = [
    int(
        match[
            "line"
        ]
    )
    for match in fetch_matches
]

fetch_excerpts = [
    source_excerpt(
        api_source,
        max(
            1,
            line_number - 12,
        ),
        line_number + 28,
    )
    for line_number in fetch_line_numbers
]

has_abort_controller = (
    "AbortController"
    in api_source
)

has_abort_signal = (
    "signal:"
    in api_source
    or "signal,"
    in api_source
)

has_timeout_timer = (
    "setTimeout"
    in api_source
)

has_timer_cleanup = (
    "clearTimeout"
    in api_source
)

has_abort_error_mapping = (
    "AbortError"
    in api_source
)

timeout_gap_confirmed = not (
    has_abort_controller
    and has_abort_signal
    and has_timeout_timer
    and has_timer_cleanup
)

report: dict[str, Any] = {
    "milestone": "11.2A",
    "created_at": datetime.now().isoformat(),
    "mode": "read-only",
    "application_files_modified": False,
    "paths": {
        "api_js": str(
            API_PATH
        ),
        "app_jsx": str(
            APP_PATH
        ),
        "speech_py": str(
            SPEECH_PATH
        ),
    },
    "api_client": {
        "fetch_call_count": len(
            fetch_matches
        ),
        "fetch_lines": fetch_line_numbers,
        "has_response_ok_check": (
            "response.ok"
            in api_source
        ),
        "has_error_throwing": (
            "throw new Error"
            in api_source
        ),
        "has_abort_controller": (
            has_abort_controller
        ),
        "has_abort_signal": (
            has_abort_signal
        ),
        "has_timeout_timer": (
            has_timeout_timer
        ),
        "has_timer_cleanup": (
            has_timer_cleanup
        ),
        "has_abort_error_mapping": (
            has_abort_error_mapping
        ),
        "timeout_gap_confirmed": (
            timeout_gap_confirmed
        ),
    },
    "frontend": {
        "has_generating_state": (
            "generating"
            in app_source
        ),
        "has_set_generating": (
            "setGenerating"
            in app_source
        ),
        "has_error_state": (
            "setError"
            in app_source
        ),
    },
    "backend": {
        "has_503_mapping": (
            "status_code=503"
            in speech_source
        ),
        "has_502_mapping": (
            "status_code=502"
            in speech_source
        ),
        "has_500_mapping": (
            "status_code=500"
            in speech_source
        ),
    },
    "matches": {
        "fetch": fetch_matches,
        "api_errors": api_error_matches,
        "timeouts": timeout_matches,
        "frontend_state": app_state_matches,
        "backend_errors": backend_error_matches,
    },
    "fetch_excerpts": fetch_excerpts,
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
    "Preflight report was saved",
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
print("FRONTEND API CLIENT BASELINE")
print("=" * 92)

print(
    "Fetch call count       :",
    len(
        fetch_matches
    ),
)

print(
    "Response success check :",
    "response.ok"
    in api_source,
)

print(
    "Readable error mapping :",
    "throw new Error"
    in api_source,
)

print(
    "AbortController        :",
    has_abort_controller,
)

print(
    "Fetch signal           :",
    has_abort_signal,
)

print(
    "Timeout timer          :",
    has_timeout_timer,
)

print(
    "Timer cleanup          :",
    has_timer_cleanup,
)

print(
    "Abort error mapping    :",
    has_abort_error_mapping,
)

print(
    "Timeout gap confirmed  :",
    timeout_gap_confirmed,
)

print_matches(
    "API FETCH AND ERROR MARKERS",
    fetch_matches
    + api_error_matches,
)

print_matches(
    "API TIMEOUT AND CANCELLATION MARKERS",
    timeout_matches,
)

print_matches(
    "FRONTEND GENERATION-STATE MARKERS",
    app_state_matches,
)

print_matches(
    "BACKEND ERROR-STATUS MARKERS",
    backend_error_matches,
)

print()
print("=" * 92)
print("FETCH CALL EXCERPTS")
print("=" * 92)

for index, excerpt in enumerate(
    fetch_excerpts,
    start=1,
):
    print()
    print(
        f"--- FETCH EXCERPT {index} ---"
    )

    print(
        excerpt
    )

print()
print("=" * 92)

print(
    "MILESTONE 11.2A FRONTEND REQUEST "
    "RELIABILITY PREFLIGHT: COMPLETE"
)

print("=" * 92)

print(
    "Checks passed:",
    checks_passed,
)

print(
    "Application files modified: NO"
)

print()
print(
    "Report:",
    REPORT_PATH,
)
