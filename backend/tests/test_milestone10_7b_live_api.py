from __future__ import annotations

import requests


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


print("=" * 92)
print(
    "MILESTONE 10.7B — LIVE STYLE "
    "OPENAPI AND HISTORY CONTRACT"
)
print("=" * 92)

health_response = requests.get(
    f"{BASE_URL}/health",
    timeout=15,
)

check(
    "Backend is healthy",
    health_response.status_code == 200,
    health_response.text,
)

openapi_response = requests.get(
    f"{BASE_URL}/openapi.json",
    timeout=30,
)

check(
    "OpenAPI document is readable",
    openapi_response.status_code == 200,
    openapi_response.text[:500],
)

openapi = openapi_response.json()

request_schema = (
    openapi[
        "components"
    ][
        "schemas"
    ][
        "GenerateSpeechRequest"
    ]
)

style_schema = request_schema[
    "properties"
].get(
    "style"
)

check(
    "OpenAPI request exposes style",
    isinstance(
        style_schema,
        dict,
    ),
    repr(style_schema),
)

style_reference = (
    style_schema.get("$ref")
    if isinstance(
        style_schema,
        dict,
    )
    else None
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
    "OpenAPI exposes all locked style values",
    set(
        resolved_style_schema.get(
            "enum",
            [],
        )
    )
    == EXPECTED_STYLES,
    repr(resolved_style_schema),
)

default_style = style_schema.get(
    "default"
)

if default_style is None:
    default_style = (
        resolved_style_schema
        .get(
            "default"
        )
    )

check(
    "OpenAPI style defaults to neutral",
    default_style == "neutral",
    repr(default_style),
)

history_response = requests.get(
    f"{BASE_URL}/speech/history",
    timeout=30,
)

check(
    "History endpoint is readable",
    history_response.status_code == 200,
    history_response.text[:500],
)

history = history_response.json()

check(
    "History response is a list",
    isinstance(
        history,
        list,
    ),
)

check(
    "Every history row exposes a valid style",
    all(
        item.get(
            "style"
        )
        in EXPECTED_STYLES
        for item in history
    ),
    repr(
        [
            {
                "id": item.get("id"),
                "style": item.get("style"),
            }
            for item in history
        ]
    ),
)

print()
print("=" * 92)
print(
    "MILESTONE 10.7B LIVE STYLE "
    "API CONTRACT: PASSED"
)
print("=" * 92)
print("Checks passed:", checks_passed)
