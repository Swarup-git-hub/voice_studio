from __future__ import annotations

from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent

START_PATH = (
    PROJECT_ROOT
    / "start_ai_voice_studio.ps1"
)

source = START_PATH.read_text(
    encoding="utf-8-sig"
)

invalid_marker = "$Name:"
valid_marker = "${Name}:"

invalid_count = source.count(
    invalid_marker
)

if invalid_count != 3:
    raise RuntimeError(
        "Expected exactly three invalid $Name: "
        "interpolations, found "
        f"{invalid_count}."
    )

updated_source = source.replace(
    invalid_marker,
    valid_marker,
)

if invalid_marker in updated_source:
    raise RuntimeError(
        "An invalid $Name: interpolation remains."
    )

if updated_source.count(
    valid_marker
) != 3:
    raise RuntimeError(
        "Expected exactly three repaired ${Name}: "
        "interpolations."
    )

required_statuses = [
    '${Name}: ALREADY HEALTHY',
    '${Name}: STARTING',
    '${Name}: HEALTHY',
]

for marker in required_statuses:
    if marker not in updated_source:
        raise RuntimeError(
            "Repaired startup script is missing: "
            f"{marker}"
        )

START_PATH.write_text(
    updated_source,
    encoding="utf-8",
)

print(
    "Milestone 11.1B startup-manager "
    "variable interpolation: REPAIRED"
)
