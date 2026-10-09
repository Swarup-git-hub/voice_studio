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

old_block = '''    services = @(
        $serviceStates
    )
'''

new_block = '''    services = [object[]](
        $serviceStates.ToArray()
    )
'''

old_count = source.count(
    old_block
)

if old_count != 1:
    raise RuntimeError(
        "Expected exactly one generic-list state block, "
        f"found {old_count}."
    )

updated_source = source.replace(
    old_block,
    new_block,
    1,
)

required_markers = [
    "services = [object[]](",
    "$serviceStates.ToArray()",
    "ConvertTo-Json",
    "Set-Content",
]

for marker in required_markers:
    if marker not in updated_source:
        raise RuntimeError(
            "Updated startup manager is missing marker: "
            f"{marker}"
        )

if old_block in updated_source:
    raise RuntimeError(
        "The incompatible generic-list block remains."
    )

START_PATH.write_text(
    updated_source,
    encoding="utf-8",
)

print(
    "Milestone 11.1B state-list "
    "serialization: REPAIRED"
)
