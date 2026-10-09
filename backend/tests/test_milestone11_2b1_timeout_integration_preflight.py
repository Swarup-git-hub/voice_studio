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

REPORT_PATH = (
    BACKEND_ROOT
    / "milestone_reports"
    / "milestone11_2b1_timeout_integration_preflight.json"
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


def find_lines(
    source: str,
    pattern: str,
    *,
    regex: bool = False,
) -> list[int]:
    results: list[int] = []

    compiled = (
        re.compile(
            pattern
        )
        if regex
        else None
    )

    for line_number, line in enumerate(
        source.splitlines(),
        start=1,
    ):
        matched = (
            compiled.search(
                line
            )
            is not None
            if compiled
            else pattern in line
        )

        if matched:
            results.append(
                line_number
            )

    return results


def excerpt(
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


def nearest_function_start(
    source: str,
    target_line: int,
) -> int:
    lines = source.splitlines()

    function_patterns = [
        re.compile(
            r"^\s*(?:export\s+)?async\s+function\s+\w+"
        ),
        re.compile(
            r"^\s*(?:export\s+)?function\s+\w+"
        ),
        re.compile(
            r"^\s*(?:export\s+)?const\s+\w+\s*=\s*async"
        ),
        re.compile(
            r"^\s*(?:export\s+)?const\s+\w+\s*="
        ),
    ]

    for line_index in range(
        target_line - 1,
        -1,
        -1,
    ):
        line = lines[
            line_index
        ]

        if any(
            pattern.search(
                line
            )
            for pattern in function_patterns
        ):
            return (
                line_index
                + 1
            )

    return max(
        1,
        target_line - 25,
    )


def print_section(
    title: str,
    text: str,
) -> None:
    print()
    print("=" * 92)
    print(title)
    print("=" * 92)
    print(
        text
        if text
        else "No matching source section found."
    )


print("=" * 92)
print(
    "MILESTONE 11.2B-1 — FRONTEND TIMEOUT "
    "INTEGRATION PREFLIGHT"
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

api_source = API_PATH.read_text(
    encoding="utf-8-sig",
)

app_source = APP_PATH.read_text(
    encoding="utf-8-sig",
)

fetch_lines = find_lines(
    api_source,
    "fetch(",
)

check(
    "Exactly one shared fetch call exists",
    len(
        fetch_lines
    )
    == 1,
    repr(
        fetch_lines
    ),
)

fetch_line = fetch_lines[0]

request_start = nearest_function_start(
    api_source,
    fetch_line,
)

request_excerpt = excerpt(
    api_source,
    max(
        1,
        request_start - 5,
    ),
    fetch_line + 65,
)

generate_api_lines = find_lines(
    api_source,
    "generateSpeech",
)

check(
    "API client defines generateSpeech",
    bool(
        generate_api_lines
    ),
    repr(
        generate_api_lines
    ),
)

generate_api_excerpt = "\n\n".join(
    excerpt(
        api_source,
        max(
            1,
            line_number - 20,
        ),
        line_number + 35,
    )
    for line_number in generate_api_lines
)

handle_generate_lines = find_lines(
    app_source,
    r"\bhandleGenerate\b",
    regex=True,
)

check(
    "Frontend defines handleGenerate",
    bool(
        handle_generate_lines
    ),
    repr(
        handle_generate_lines
    ),
)

handle_generate_excerpt = "\n\n".join(
    excerpt(
        app_source,
        max(
            1,
            line_number - 10,
        ),
        line_number + 70,
    )
    for line_number in handle_generate_lines[
        :2
    ]
)

button_lines = find_lines(
    app_source,
    "Generate narration",
)

check(
    "Frontend contains the generation button",
    bool(
        button_lines
    ),
    repr(
        button_lines
    ),
)

button_excerpt = "\n\n".join(
    excerpt(
        app_source,
        max(
            1,
            line_number - 30,
        ),
        line_number + 20,
    )
    for line_number in button_lines
)

api_method_lines = find_lines(
    api_source,
    r"^\s*[A-Za-z_$][\w$]*\s*:",
    regex=True,
)

api_method_excerpt = "\n".join(
    excerpt(
        api_source,
        line_number,
        line_number,
    )
    for line_number in api_method_lines
)

existing_signal_lines = find_lines(
    api_source,
    r"\bsignal\b",
    regex=True,
)

existing_timeout_lines = find_lines(
    api_source,
    r"AbortController|AbortSignal|setTimeout|clearTimeout|timeout|AbortError",
    regex=True,
)

check(
    "No existing AbortController implementation exists",
    "AbortController"
    not in api_source,
)

check(
    "No existing request timer exists",
    (
        "setTimeout"
        not in api_source
        and "clearTimeout"
        not in api_source
    ),
)

check(
    "No existing AbortError mapping exists",
    "AbortError"
    not in api_source,
)

check(
    "Current request helper checks response.ok",
    "response.ok"
    in request_excerpt,
)

check(
    "Current request helper maps connection failures",
    "Could not connect to the backend"
    in request_excerpt,
)

check(
    "Generation request uses the shared API client",
    (
        "api.generateSpeech"
        in app_source
    ),
)

check(
    "Generation finally resets loading state",
    (
        "finally"
        in handle_generate_excerpt
        and "setGenerating(false)"
        in handle_generate_excerpt
    ),
)

report: dict[str, Any] = {
    "milestone": "11.2B-1",
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
    },
    "request_helper": {
        "fetch_line": fetch_line,
        "function_start_line": request_start,
        "excerpt": request_excerpt,
    },
    "generate_speech": {
        "api_lines": generate_api_lines,
        "api_excerpt": generate_api_excerpt,
        "app_lines": handle_generate_lines,
        "app_excerpt": handle_generate_excerpt,
        "button_lines": button_lines,
        "button_excerpt": button_excerpt,
    },
    "api_method_lines": api_method_lines,
    "existing_signal_lines": existing_signal_lines,
    "existing_timeout_lines": existing_timeout_lines,
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

print_section(
    "SHARED REQUEST HELPER",
    request_excerpt,
)

print_section(
    "GENERATE SPEECH API METHOD",
    generate_api_excerpt,
)

print_section(
    "FRONTEND HANDLE GENERATE",
    handle_generate_excerpt,
)

print_section(
    "GENERATION BUTTON",
    button_excerpt,
)

print_section(
    "API METHOD REGISTRY LINES",
    api_method_excerpt,
)

print()
print("=" * 92)
print("EXISTING RELIABILITY MARKERS")
print("=" * 92)

print(
    "Signal lines :",
    existing_signal_lines,
)

print(
    "Timeout lines:",
    existing_timeout_lines,
)

print()
print("=" * 92)

print(
    "MILESTONE 11.2B-1 FRONTEND TIMEOUT "
    "INTEGRATION PREFLIGHT: PASSED"
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
