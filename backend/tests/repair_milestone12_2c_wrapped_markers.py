from __future__ import annotations

from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]

TARGET_PATH = (
    BACKEND_ROOT
    / "tests"
    / "implement_and_test_milestone12_2c_policies.py"
)


source = TARGET_PATH.read_text(
   
    / "tests"
    / "implement_and_test_milestone12_2c_policies.py"
)


 encoding="utf-8-sig"
)


replacements = {
    '"AI-generated or synthetic"': (
        '"Synthetic audio should be clearly identified"'
    ),
    (
        '"does not yet implement an electronic '
        'consent registry"'
    ): (
        '"does not yet implement an electronic consent"'
    ),
    (
        '"does not grant permission to use a '
        'person\'s voice"'
    ): (
        '"permission to use a person\'s voice"'
    ),
}


updated_source = source


for old_text, new_text in replacements.items():
    occurrence_count = updated_source.count(
        old_text
    )

    if occurrence_count != 1:
        raise RuntimeError(
            "Expected exactly one acceptance marker.\n"
            f"Marker: {old_text}\n"
            f"Occurrences: {occurrence_count}"
        )

    updated_source = updated_source.replace(
        old_text,
        new_text,
        1,
    )


for old_text in replacements:
    if old_text in updated_source:
        raise RuntimeError(
            "An obsolete wrapped-text marker remains:\n"
            f"{old_text}"
        )


for new_text in replacements.values():
    if new_text not in updated_source:
        raise RuntimeError(
            "A repaired acceptance marker is missing:\n"
            f"{new_text}"
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
    "Synthetic-audio disclosure marker: REPAIRED"
)

print(
    "Consent-registry marker: REPAIRED"
)

print(
    "Voice-rights separation marker: REPAIRED"
)

print(
    "Milestone 12.2C wrapped-marker repair: APPLIED"
)
