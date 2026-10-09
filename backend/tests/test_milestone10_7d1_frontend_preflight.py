from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.request import urlopen


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
FRONTEND_ROOT = PROJECT_ROOT / "frontend"

APP_PATH = (
    FRONTEND_ROOT
    / "src"
    / "App.jsx"
)

CSS_PATH = (
    FRONTEND_ROOT
    / "src"
    / "App.css"
)

API_PATH = (
    FRONTEND_ROOT
    / "src"
    / "api.js"
)

PACKAGE_PATH = (
    FRONTEND_ROOT
    / "package.json"
)

REPORT_PATH = (
    BACKEND_ROOT
    / "milestone_reports"
    / "milestone10_7d1_frontend_preflight.json"
)

BASE_URL = "http://127.0.0.1:8000"

EXPECTED_STYLES = {
    "neutral",
    "professional",
    "energetic",
    "calm",
    "storytelling",
}


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

        raise AssertionError(message)

    checks_passed += 1
    print(f"{name}: PASSED")


def read_source(
    path: Path,
) -> str:
    return path.read_text(
        encoding="utf-8-sig",
    )


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as source_file:
        while True:
            block = source_file.read(
                1024 * 1024
            )

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


def fetch_json(
    url: str,
    timeout: int = 30,
) -> tuple[int, Any]:
    try:
        with urlopen(
            url,
            timeout=timeout,
        ) as response:
            body = response.read()

            return (
                response.status,
                json.loads(
                    body.decode("utf-8")
                ),
            )

    except HTTPError as error:
        error_body = error.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            f"HTTP {error.code} from {url}\n"
            f"{error_body}"
        ) from error

    except URLError as error:
        raise RuntimeError(
            f"Could not connect to {url}: {error}"
        ) from error


def find_line_numbers(
    source: str,
    marker: str,
) -> list[int]:
    return [
        line_number
        for line_number, line
        in enumerate(
            source.splitlines(),
            start=1,
        )
        if marker in line
    ]


def source_context(
    source: str,
    marker: str,
    before: int = 12,
    after: int = 30,
) -> list[dict[str, Any]]:
    lines = source.splitlines()
    contexts: list[dict[str, Any]] = []

    for match_line in find_line_numbers(
        source,
        marker,
    ):
        start_line = max(
            1,
            match_line - before,
        )

        end_line = min(
            len(lines),
            match_line + after,
        )

        numbered_lines = [
            f"{line_number:4d}: "
            f"{lines[line_number - 1]}"
            for line_number
            in range(
                start_line,
                end_line + 1,
            )
        ]

        contexts.append(
            {
                "marker": marker,
                "match_line": match_line,
                "start_line": start_line,
                "end_line": end_line,
                "lines": numbered_lines,
            }
        )

    return contexts


def print_context_group(
    title: str,
    contexts: list[dict[str, Any]],
) -> None:
    print()
    print("=" * 92)
    print(title)
    print("=" * 92)

    if not contexts:
        print("No matching context was found.")
        return

    for index, context in enumerate(
        contexts,
        start=1,
    ):
        print()
        print(
            f"Context {index}: "
            f"line {context['match_line']}"
        )

        print("-" * 92)

        for rendered_line in context["lines"]:
            print(rendered_line)


print("=" * 92)
print(
    "MILESTONE 10.7D-1 — FRONTEND "
    "STYLE INTEGRATION PREFLIGHT"
)
print("=" * 92)

required_paths = {
    "App.jsx": APP_PATH,
    "App.css": CSS_PATH,
    "api.js": API_PATH,
    "package.json": PACKAGE_PATH,
}

missing_paths = {
    name: str(path)
    for name, path in required_paths.items()
    if not path.exists()
}

check(
    "All required frontend files exist",
    not missing_paths,
    json.dumps(
        missing_paths,
        indent=2,
    ),
)

app_source = read_source(
    APP_PATH
)

css_source = read_source(
    CSS_PATH
)

api_source = read_source(
    API_PATH
)

package_data = json.loads(
    read_source(
        PACKAGE_PATH
    )
)

scripts = package_data.get(
    "scripts",
    {}
)

check(
    "Frontend package is private",
    package_data.get("private") is True,
)

check(
    "Frontend has a Vite development command",
    scripts.get("dev") == "vite",
    repr(scripts),
)

check(
    "Frontend has a production build command",
    scripts.get("build") == "vite build",
    repr(scripts),
)

check(
    "App imports its stylesheet",
    'import "./App.css";'
    in app_source,
)

check(
    "Frontend API exposes speech generation",
    "generateSpeech(payload)"
    in api_source,
)

check(
    "Frontend has engine labels",
    "const ENGINE_LABELS"
    in app_source,
)

check(
    "Frontend has Auto engine state",
    (
        'const [engine, setEngine] '
        '= useState("auto");'
        in app_source
    ),
)

check(
    "Frontend has fallback state",
    (
        "const [allowFallback, "
        "setAllowFallback]"
        in app_source
    ),
)

check(
    "Frontend has latest-generation state",
    (
        "const [latestGeneration, "
        "setLatestGeneration]"
        in app_source
    ),
)

check(
    "Frontend has history state",
    (
        "const [history, setHistory]"
        in app_source
    ),
)

check(
    "Generation payload contains engine",
    "        engine,"
    in app_source,
)

check(
    "Generation payload contains fallback",
    "allow_fallback:"
    in app_source,
)

check(
    "Frontend currently has no style state",
    (
        "const [style, setStyle]"
        not in app_source
    ),
)

check(
    "Frontend currently sends no style",
    (
        "        style,"
        not in app_source
    ),
)

check(
    "Frontend currently has no style label map",
    "STYLE_LABELS"
    not in app_source,
)

check(
    "Frontend stylesheet is non-empty",
    bool(
        css_source.strip()
    ),
)

health_status, health = fetch_json(
    f"{BASE_URL}/health",
    timeout=15,
)

check(
    "Backend is healthy",
    health_status == 200,
    repr(health),
)

openapi_status, openapi = fetch_json(
    f"{BASE_URL}/openapi.json",
    timeout=30,
)

check(
    "Backend OpenAPI is readable",
    openapi_status == 200,
)

request_schema = (
    openapi[
        "components"
    ][
        "schemas"
    ][
        "GenerateSpeechRequest"
    ]
)

style_schema = (
    request_schema[
        "properties"
    ].get(
        "style"
    )
)

check(
    "Backend OpenAPI exposes style",
    isinstance(
        style_schema,
        dict,
    ),
    repr(style_schema),
)

style_reference = style_schema.get(
    "$ref"
)

if style_reference:
    style_schema_name = (
        style_reference
        .rsplit(
            "/",
            1,
        )[-1]
    )

    resolved_style_schema = (
        openapi[
            "components"
        ][
            "schemas"
        ][
            style_schema_name
        ]
    )
else:
    resolved_style_schema = style_schema

check(
    "Backend exposes all five style values",
    set(
        resolved_style_schema.get(
            "enum",
            [],
        )
    )
    == EXPECTED_STYLES,
    repr(resolved_style_schema),
)

style_default = style_schema.get(
    "default"
)

if style_default is None:
    style_default = (
        resolved_style_schema.get(
            "default"
        )
    )

check(
    "Backend style default is neutral",
    style_default == "neutral",
    repr(style_default),
)

contexts = {
    "state_block": source_context(
        app_source,
        "const [engine, setEngine]",
        before=10,
        after=20,
    ),
    "generation_payload": source_context(
        app_source,
        "api.generateSpeech",
        before=20,
        after=35,
    ),
    "engine_ui": source_context(
        app_source,
        "setEngine",
        before=18,
        after=45,
    ),
    "latest_generation": source_context(
        app_source,
        "latestGeneration",
        before=15,
        after=45,
    ),
    "history_rendering": source_context(
        app_source,
        "history.map",
        before=20,
        after=65,
    ),
}

check(
    "Engine-state context was captured",
    bool(
        contexts["state_block"]
    ),
)

check(
    "Generation-payload context was captured",
    bool(
        contexts["generation_payload"]
    ),
)

check(
    "Engine UI context was captured",
    len(
        contexts["engine_ui"]
    )
    >= 2,
    (
        "Expected state and UI occurrences; "
        f"found {len(contexts['engine_ui'])}."
    ),
)

check(
    "Latest-generation context was captured",
    bool(
        contexts["latest_generation"]
    ),
)

check(
    "History-rendering context was captured",
    bool(
        contexts["history_rendering"]
    ),
)

report = {
    "milestone": "10.7D-1",
    "captured_at": datetime.now().isoformat(),
    "project_root": str(PROJECT_ROOT),
    "frontend_root": str(FRONTEND_ROOT),
    "backend_style_values": sorted(
        EXPECTED_STYLES
    ),
    "backend_style_default": (
        style_default
    ),
    "package_scripts": scripts,
    "source_hashes": {
        name: {
            "path": str(path),
            "sha256": sha256_file(path),
        }
        for name, path
        in required_paths.items()
    },
    "contexts": contexts,
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
    "Frontend preflight report was written",
    (
        REPORT_PATH.exists()
        and REPORT_PATH.stat().st_size
        > 0
    ),
    str(REPORT_PATH),
)

print_context_group(
    "STATE BLOCK",
    contexts["state_block"],
)

print_context_group(
    "GENERATION PAYLOAD",
    contexts["generation_payload"],
)

print_context_group(
    "ENGINE UI OCCURRENCES",
    contexts["engine_ui"],
)

print_context_group(
    "LATEST GENERATION OCCURRENCES",
    contexts["latest_generation"],
)

print_context_group(
    "HISTORY RENDERING",
    contexts["history_rendering"],
)

print()
print("Preflight report:", REPORT_PATH)

print()
print("=" * 92)
print(
    "MILESTONE 10.7D-1 FRONTEND "
    "INTEGRATION PREFLIGHT: PASSED"
)
print("=" * 92)
print("Checks passed:", checks_passed)
