from __future__ import annotations

from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]

TEST_PATH = (
    BACKEND_ROOT
    / "tests"
    / "test_milestone12_1b_release_hygiene.py"
)


source = TEST_PATH.read_text(
    encoding="utf-8-sig"
)


old_block = '''check(
    "Environment example contains no Windows absolute paths",
    re.search(
        r"[A-Za-z]:[\\\\/]",
        example_source,
    )
    is None,
)
'''


new_block = '''unsafe_windows_absolute_paths = {
    key: value
    for key, value in example_assignments
    if re.match(
        r"""^\\s*["']?[A-Za-z]:[\\\\/]""",
        value,
    )
}

check(
    "Environment example contains no Windows absolute paths",
    not unsafe_windows_absolute_paths,
    repr(
        unsafe_windows_absolute_paths
    ),
)
'''


old_count = source.count(
    old_block
)

if old_count != 1:
    raise RuntimeError(
        "Expected exactly one original Windows-path "
        f"acceptance block, found {old_count}."
    )


updated_source = source.replace(
    old_block,
    new_block,
    1,
)


required_markers = [
    "unsafe_windows_absolute_paths",
    "for key, value in example_assignments",
    'r"""^\\\\s*["\\\']?[A-Za-z]:[\\\\\\\\/]"""',
    "not unsafe_windows_absolute_paths",
]

for marker in required_markers:
    if marker not in updated_source:
        raise RuntimeError(
            "Updated test is missing marker: "
            f"{marker}"
        )


if old_block in updated_source:
    raise RuntimeError(
        "The false-positive Windows-path check remains."
    )


compile(
    updated_source,
    str(
        TEST_PATH
    ),
    "exec",
)


TEST_PATH.write_text(
    updated_source,
    encoding="utf-8",
)


print(
    "Milestone 12.1B Windows-path false-positive "
    "acceptance check: FIXED"
)
