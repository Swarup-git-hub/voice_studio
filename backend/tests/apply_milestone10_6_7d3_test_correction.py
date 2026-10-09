from __future__ import annotations

from pathlib import Path


backend_root = Path(__file__).resolve().parents[1]

test_path = (
    backend_root
    / "tests"
    / "test_live_auto_romanized_telugu.py"
)

source = test_path.read_text(
    encoding="utf-8"
)

old_block = '''check(
    "Segmented routing was recorded",
    routing_reason.startswith(
        "segmented_phrase_routing:"
    ),
    routing_reason,
)

route_engine_summary = (
    routing_reason
    .rsplit(
        ":",
        1,
    )[-1]
    .split(",")
)
'''

new_block = '''check(
    "Romanized Telugu routing was recorded",
    (
        routing_reason
        == "auto_romanized_telugu_indicf5_primary"
        or routing_reason.startswith(
            "segmented_phrase_routing:"
        )
    ),
    routing_reason,
)

if routing_reason.startswith(
    "segmented_phrase_routing:"
):
    route_engine_summary = (
        routing_reason
        .rsplit(
            ":",
            1,
        )[-1]
        .split(",")
    )
else:
    route_engine_summary = [
        "indicf5"
    ]
'''

if new_block not in source:
    if source.count(old_block) != 1:
        raise RuntimeError(
            "Could not find exactly one obsolete "
            "Romanized Telugu routing assertion."
        )

    source = source.replace(
        old_block,
        new_block,
        1,
    )

test_path.write_text(
    source,
    encoding="utf-8",
)

updated = test_path.read_text(
    encoding="utf-8"
)

required_markers = [
    "auto_romanized_telugu_indicf5_primary",
    "Romanized Telugu routing was recorded",
    'route_engine_summary = [\n        "indicf5"\n    ]',
]

for marker in required_markers:
    if marker not in updated:
        raise RuntimeError(
            f"Missing corrected test marker: {marker}"
        )

print(
    "Milestone 10.6.7D-3 routing test "
    "expectation: CORRECTED"
)
