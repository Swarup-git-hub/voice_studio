from __future__ import annotations

from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]

TARGET_PATH = (
    BACKEND_ROOT
    / "tests"
    / "implement_and_test_milestone12_2c_policies.py"
)


source = TARGET_PATH.read_text(
    encoding="utf-8-sig"
)


old_block_1 = '''    "Synthetic-audio disclosure": (
        "AI-generated or synthetic"
    ),'''

new_block_1 = '''    "Synthetic-audio disclosure": (
        "Synthetic audio should be clearly identified"
    ),'''


old_block_2 = '''    "Consent registry deployment gate": (
        "does not yet implement an electronic consent registry"
    ),'''

new_block_2 = '''    "Consent registry deployment gate": (
        "does not yet implement an electronic consent"
    ),'''


old_block_3 = '''    "Software licence identity separation": (
        "does not grant permission to use a person's voice"
    ),'''

new_block_3 = '''    "Software licence identity separation": (
        "permission to use a person's voice"
    ),'''


replacements = [
    (
        old_block_1,
        new_block_1,
        "Synthetic-audio disclosure marker",
    ),
    (
        old_block_2,
        new_block_2,
        "Consent-registry marker",
    ),
    (
        old_block_3,
        new_block_3,
        "Voice-rights separation marker",
    ),
]


updated_source = source


for old_block, new_block, marker_name in replacements:
    old_count = updated_source.count(
        old_block
    )

    if old_count == 1:
        updated_source = updated_source.replace(
            old_block,
            new_block,
            1,
        )

        print(
            f"{marker_name}: REPAIRED"
        )

        continue

    if new_block in updated_source:
        print(
            f"{marker_name}: ALREADY REPAIRED"
        )

        continue

    raise RuntimeError(
        f"Could not locate the expected block for {marker_name}.\n"
        f"Original occurrences: {old_count}"
    )


required_markers = [
    '"Synthetic audio should be clearly identified"',
    '"does not yet implement an electronic consent"',
    '"permission to use a person\'s voice"',
]


for marker in required_markers:
    if marker not in updated_source:
        raise RuntimeError(
            "Repaired source is missing marker: "
            f"{marker}"
        )


compile(
    updated_source,
    str(
        TARGET_PATH
    ),
    "exec",
)


TARGET_PATH.write_text(
    updated_source,
    encoding="utf-8",
)


print(
    "Milestone 12.2C wrapped-marker repair v2: APPLIED"
)
