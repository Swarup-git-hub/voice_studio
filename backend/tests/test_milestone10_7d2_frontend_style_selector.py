from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.request import urlopen


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent

FRONTEND_ROOT = (
    PROJECT_ROOT
    / "frontend"
)

APP_PATH = (
    FRONTEND_ROOT
    / "src"
    / "App.jsx"
)

PACKAGE_PATH = (
    FRONTEND_ROOT
    / "package.json"
)

FRONTEND_URL = "http://127.0.0.1:5173"
BACKEND_URL = "http://127.0.0.1:8000"

EXPECTED_STYLE_LABELS = {
    "neutral": "Neutral",
    "professional": "Professional",
    "energetic": "Energetic",
    "calm": "Calm",
    "storytelling": "Storytelling",
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


def fetch(
    url: str,
    timeout: int = 30,
) -> tuple[int, bytes]:
    with urlopen(
        url,
        timeout=timeout,
    ) as response:
        return (
            response.status,
            response.read(),
        )


print("=" * 92)
print(
    "MILESTONE 10.7D-2 — FRONTEND "
    "STYLE SELECTOR INTEGRATION CONTRACT"
)
print("=" * 92)

check(
    "Frontend App.jsx exists",
    APP_PATH.exists(),
    str(APP_PATH),
)

check(
    "Frontend package.json exists",
    PACKAGE_PATH.exists(),
    str(PACKAGE_PATH),
)

source = read_source(
    APP_PATH
)

package_data = json.loads(
    read_source(
        PACKAGE_PATH
    )
)

check(
    "Frontend production build command remains available",
    (
        package_data
        .get(
            "scripts",
            {},
        )
        .get(
            "build"
        )
        == "vite build"
    ),
    repr(
        package_data.get(
            "scripts"
        )
    ),
)

style_block_match = re.search(
    r"const STYLE_LABELS = \{\n"
    r"(?P<body>.*?)"
    r"\n\};",
    source,
    re.DOTALL,
)

check(
    "Style label map exists",
    style_block_match is not None,
)

style_pairs = {}

if style_block_match is not None:
    style_pairs = {
        key: value
        for key, value
        in re.findall(
            r'^\s*([a-z_]+):\s*"([^"]+)",?$',
            style_block_match.group(
                "body"
            ),
            re.MULTILINE,
        )
    }

check(
    "Style label keys match the backend contract",
    set(
        style_pairs
    )
    == set(
        EXPECTED_STYLE_LABELS
    ),
    repr(style_pairs),
)

check(
    "Style labels match the locked display names",
    style_pairs == EXPECTED_STYLE_LABELS,
    repr(style_pairs),
)

check(
    "Style formatter exists",
    "function formatStyle(styleValue)"
    in source,
)

check(
    "Style state defaults to neutral",
    (
        'const [style, setStyle] '
        '= useState("neutral");'
        in source
    ),
)

check(
    "Style state exists exactly once",
    source.count(
        'const [style, setStyle] '
        '= useState("neutral");'
    )
    == 1,
)

check(
    "Generation payload sends style",
    "        style,\n"
    in source,
)

check(
    "Generation payload sends style once",
    source.count(
        "        style,\n"
    )
    == 1,
)

check(
    "Generation payload preserves cleaned source text",
    "        text: cleanText,"
    in source,
)

check(
    "Generation payload preserves engine selection",
    "        engine,"
    in source,
)

check(
    "Generation payload preserves fallback selection",
    "allow_fallback:"
    in source,
)

check(
    "Reset controls restores neutral style",
    '    setStyle("neutral");'
    in source,
)

check(
    "Voice-style selector label exists",
    (
        '<span className="field-label">'
        "Voice style</span>"
        in source
    ),
)

check(
    "Voice-style selector uses style state",
    "value={style}"
    in source,
)

check(
    "Voice-style selector updates style state",
    "setStyle(event.target.value)"
    in source,
)

check(
    "Voice-style selector is disabled while generating",
    "disabled={generating}"
    in source,
)

check(
    "Voice-style options come from the locked map",
    "Object.entries(STYLE_LABELS)"
    in source,
)

check(
    "Latest generation displays style",
    (
        "Style: "
        "{formatStyle(latestGeneration.style)}"
        in source
    ),
)

check(
    "History displays style",
    (
        "Style: "
        "{formatStyle(item.style)}"
        in source
    ),
)

frontend_status, frontend_body = fetch(
    FRONTEND_URL,
    timeout=20,
)

check(
    "Frontend development server is reachable",
    frontend_status == 200,
    (
        f"Status={frontend_status}; "
        f"Bytes={len(frontend_body)}"
    ),
)

backend_status, backend_body = fetch(
    f"{BACKEND_URL}/health",
    timeout=20,
)

check(
    "Backend remains healthy",
    backend_status == 200,
    (
        f"Status={backend_status}; "
        f"Body={backend_body[:500]!r}"
    ),
)

openapi_status, openapi_body = fetch(
    f"{BACKEND_URL}/openapi.json",
    timeout=30,
)

check(
    "Backend OpenAPI remains readable",
    openapi_status == 200,
)

openapi = json.loads(
    openapi_body.decode(
        "utf-8"
    )
)

style_schema = (
    openapi[
        "components"
    ][
        "schemas"
    ][
        "GenerateSpeechRequest"
    ][
        "properties"
    ].get(
        "style"
    )
)

check(
    "Backend OpenAPI still exposes style",
    isinstance(
        style_schema,
        dict,
    ),
    repr(style_schema),
)

style_reference = (
    style_schema.get(
        "$ref"
    )
    if isinstance(
        style_schema,
        dict,
    )
    else None
)

if style_reference:
    schema_name = (
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
            schema_name
        ]
    )
else:
    resolved_style_schema = style_schema

check(
    "Frontend styles match the backend enum",
    set(
        resolved_style_schema.get(
            "enum",
            [],
        )
    )
    == set(
        EXPECTED_STYLE_LABELS
    ),
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
    "Backend style default remains neutral",
    style_default == "neutral",
    repr(style_default),
)

print()
print("Integrated styles:")

for style_name, label in (
    EXPECTED_STYLE_LABELS.items()
):
    print(
        f"  {style_name:14s} -> {label}"
    )

print()
print("=" * 92)
print(
    "MILESTONE 10.7D-2 FRONTEND "
    "STYLE SELECTOR INTEGRATION: PASSED"
)
print("=" * 92)
print("Checks passed:", checks_passed)
