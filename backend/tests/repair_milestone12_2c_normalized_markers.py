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


existing_helper_block = '''def contains_normalized_marker(
    source: str,
    marker: str,
) -> bool:
    normalized_source = " ".join(
        source.split()
    )

    normalized_marker = " ".join(
        marker.split()
    )

    return normalized_marker in normalized_source
'''


if existing_helper_block not in source:
    insertion_anchor = '''def contains_windows_absolute_path(
    source: str,
) -> bool:
    return (
        re.search(
            r"(?m)^[A-Za-z]:[\\\\/]",
            source,
        )
        is not None
    )
'''

    if source.count(
        insertion_anchor
    ) != 1:
        raise RuntimeError(
            "Could not locate the Windows-path helper insertion anchor."
        )

    replacement_anchor = (
        insertion_anchor
        + "\n\n"
        + existing_helper_block
    )

    source = source.replace(
        insertion_anchor,
        replacement_anchor,
        1,
    )

    print(
        "Whitespace-normalised marker helper: ADDED"
    )

else:
    print(
        "Whitespace-normalised marker helper: ALREADY PRESENT"
    )


marker_replacements = [
    (
        "marker in voice_policy,",
        '''contains_normalized_marker(
            voice_policy,
            marker,
        ),''',
        "Voice-policy marker checks",
    ),
    (
        "marker in privacy_source,",
        '''contains_normalized_marker(
            privacy_source,
            marker,
        ),''',
        "Privacy marker checks",
    ),
    (
        "marker in security_source,",
        '''contains_normalized_marker(
            security_source,
            marker,
        ),''',
        "Security marker checks",
    ),
]


updated_source = source


for old_text, new_text, name in marker_replacements:
    old_count = updated_source.count(
        old_text
    )

    if old_count == 1:
        updated_source = updated_source.replace(
            old_text,
            new_text,
            1,
        )

        print(
            f"{name}: REPAIRED"
        )

        continue

    if new_text in updated_source:
        print(
            f"{name}: ALREADY REPAIRED"
        )

        continue

    raise RuntimeError(
        f"Could not locate the expected check for {name}.\n"
        f"Occurrences: {old_count}"
    )


required_markers = [
    "def contains_normalized_marker(",
    "normalized_source =",
    "normalized_marker =",
    "contains_normalized_marker(\n            voice_policy,",
    "contains_normalized_marker(\n            privacy_source,",
    "contains_normalized_marker(\n            security_source,",
]


for marker in required_markers:
    if marker not in updated_source:
        raise RuntimeError(
            "Repaired policy script is missing marker: "
            f"{marker}"
        )


compile(
    updated_source,
    str(
        TARGET_PATH
    ),
    "exec",
)


def probe_contains_normalized_marker(
    source_text: str,
    marker_text: str,
) -> bool:
    return (
        " ".join(
            marker_text.split()
        )
        in " ".join(
            source_text.split()
        )
    )


probes = [
    (
        "GitHub Private Vulnerability\nReporting through the repository",
        "Private Vulnerability Reporting",
        True,
    ),
    (
        "must not expose internal model services\ndirectly",
        "must not expose internal model services directly",
        True,
    ),
    (
        "AI-generated or\nsynthetic",
        "AI-generated or synthetic",
        True,
    ),
    (
        "unrelated security text",
        "Private Vulnerability Reporting",
        False,
    ),
]


for source_text, marker_text, expected in probes:
    actual = probe_contains_normalized_marker(
        source_text,
        marker_text,
    )

    if actual != expected:
        raise RuntimeError(
            "Whitespace-normalisation probe failed.\n"
            f"Source: {source_text!r}\n"
            f"Marker: {marker_text!r}\n"
            f"Expected: {expected}\n"
            f"Actual: {actual}"
        )


TARGET_PATH.write_text(
    updated_source,
    encoding="utf-8",
)


print(
    "Wrapped private-reporting marker probe: PASSED"
)

print(
    "Wrapped model-service marker probe: PASSED"
)

print(
    "Milestone 12.2C normalized-marker repair: APPLIED"
)
