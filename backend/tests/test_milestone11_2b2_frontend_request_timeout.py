from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent

API_PATH = (
    PROJECT_ROOT
    / "frontend"
    / "src"
    / "api.js"
)

REPORT_PATH = (
    BACKEND_ROOT
    / "milestone_reports"
    / "milestone11_2b2_frontend_request_timeout_static_test.json"
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


print("=" * 92)
print(
    "MILESTONE 11.2B-2 — FRONTEND REQUEST "
    "TIMEOUT STATIC ACCEPTANCE"
)
print("=" * 92)

check(
    "Frontend API client exists",
    API_PATH.exists(),
    str(
        API_PATH
    ),
)

source = API_PATH.read_text(
    encoding="utf-8-sig"
)

check(
    "Default timeout is two minutes",
    (
        "const DEFAULT_REQUEST_TIMEOUT_MS =\n"
        "  2 * 60 * 1000;"
    )
    in source,
)

check(
    "Voice-upload timeout is ten minutes",
    (
        "const VOICE_UPLOAD_TIMEOUT_MS =\n"
        "  10 * 60 * 1000;"
    )
    in source,
)

check(
    "Speech-generation timeout is thirty minutes",
    (
        "const SPEECH_GENERATION_TIMEOUT_MS =\n"
        "  30 * 60 * 1000;"
    )
    in source,
)

check(
    "Timeout duration formatter exists",
    "function formatTimeoutDuration(timeoutMs)"
    in source,
)

check(
    "Readable timeout error factory exists",
    "function getTimeoutError(timeoutMs)"
    in source,
)

check(
    "Request helper accepts a custom timeout",
    "timeoutMs = DEFAULT_REQUEST_TIMEOUT_MS"
    in source,
)

check(
    "Request helper accepts an external signal",
    "signal: externalSignal"
    in source,
)

check(
    "Request helper creates one AbortController",
    source.count(
        "new AbortController()"
    )
    == 1,
)

check(
    "Request helper creates a timeout timer",
    "const timeoutId = setTimeout("
    in source,
)

check(
    "Timeout callback marks the timeout cause",
    "timeoutTriggered = true;"
    in source,
)

check(
    "Timeout callback aborts the fetch",
    (
        "timeoutTriggered = true;\n"
        "      controller.abort();"
    )
    in source,
)

check(
    "Controlled signal is passed to fetch",
    "signal: controller.signal"
    in source,
)

check(
    "Timeouts receive a distinct readable error",
    (
        "if (timeoutTriggered)"
        in source
        and "throw getTimeoutError("
        in source
    ),
)

check(
    "Manual cancellation receives a distinct error",
    (
        'error?.name === "AbortError"'
        in source
        and '"The request was cancelled."'
        in source
    ),
)

check(
    "Backend connection error remains available",
    "Could not connect to the backend."
    in source,
)

check(
    "Timeout timer is always cleared",
    "clearTimeout("
    in source,
)

check(
    "External abort listener is removed",
    "externalSignal.removeEventListener("
    in source,
)

check(
    "Custom timeout option is not passed to fetch",
    (
        "...fetchOptions"
        in source
        and "        ...options,\n"
        not in source
    ),
)

check(
    "FormData detection uses cleaned fetch options",
    "fetchOptions.body instanceof FormData"
    in source,
)

check(
    "Multipart Content-Type protection remains",
    "Do not manually set Content-Type for FormData."
    in source,
)

check(
    "HTTP response status handling remains",
    "if (!response.ok)"
    in source,
)

check(
    "HTTP 204 handling remains",
    "if (response.status === 204)"
    in source,
)

check(
    "JSON response handling remains",
    'contentType.includes("application/json")'
    in source,
)

check(
    "Voice upload receives its longer timeout",
    source.count(
        "timeoutMs: VOICE_UPLOAD_TIMEOUT_MS"
    )
    == 1,
)

check(
    "Speech generation receives its longer timeout",
    source.count(
        "timeoutMs: SPEECH_GENERATION_TIMEOUT_MS"
    )
    == 1,
)

check(
    "Only one shared fetch call remains",
    source.count(
        "fetch("
    )
    == 1,
)

check(
    "Only one shared request helper remains",
    source.count(
        "async function request(path, options = {})"
    )
    == 1,
)


report = {
    "milestone": "11.2B-2",
    "created_at": datetime.now().isoformat(),
    "mode": "static acceptance",
    "checks_passed": checks_passed,
    "api_path": str(
        API_PATH
    ),
    "timeouts_ms": {
        "default": 120000,
        "voice_upload": 600000,
        "speech_generation": 1800000,
    },
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
    "Static acceptance report was saved",
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
    "MILESTONE 11.2B-2 FRONTEND REQUEST "
    "TIMEOUT STATIC ACCEPTANCE: PASSED"
)

print("=" * 92)

print(
    "Checks passed:",
    checks_passed,
)

print()
print(
    "Report:",
    REPORT_PATH,
)
