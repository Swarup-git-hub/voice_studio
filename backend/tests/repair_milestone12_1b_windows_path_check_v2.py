from __future__ import annotations

import ast
import re
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]

TEST_PATH = (
    BACKEND_ROOT
    / "tests"
    / "test_milestone12_1b_release_hygiene.py"
)

TARGET_CHECK_NAME = (
    "Environment example contains no Windows absolute paths"
)


source = TEST_PATH.read_text(
    encoding="utf-8-sig"
)

tree = ast.parse(
    source,
    filename=str(
        TEST_PATH
    ),
)


matching_nodes: list[ast.Expr] = []


for node in tree.body:
    if not isinstance(
        node,
        ast.Expr,
    ):
        continue

    call = node.value

    if not isinstance(
        call,
        ast.Call,
    ):
        continue

    if not (
        isinstance(
            call.func,
            ast.Name,
        )
        and call.func.id == "check"
    ):
        continue

    if not call.args:
        continue

    first_argument = call.args[0]

    if (
        isinstance(
            first_argument,
            ast.Constant,
        )
        and first_argument.value
        == TARGET_CHECK_NAME
    ):
        matching_nodes.append(
            node
        )


if len(
    matching_nodes
) != 1:
    raise RuntimeError(
        "Expected exactly one Windows absolute-path "
        f"acceptance check, found {len(matching_nodes)}."
    )


target_node = matching_nodes[0]

if target_node.end_lineno is None:
    raise RuntimeError(
        "Python did not provide the end line of the target check."
    )


replacement_block = '''unsafe_windows_absolute_paths = {
    key: value
    for key, value in example_assignments
    if re.match(
        r"^[A-Za-z]:[\\\\/]",
        value.strip()
        .strip('"')
        .strip("'"),
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


source_lines = source.splitlines(
    keepends=True
)

start_index = (
    target_node.lineno
    - 1
)

end_index = target_node.end_lineno


updated_source = "".join(
    source_lines[:start_index]
    + [
        replacement_block
    ]
    + source_lines[end_index:]
)


compile(
    updated_source,
    str(
        TEST_PATH
    ),
    "exec",
)


updated_tree = ast.parse(
    updated_source,
    filename=str(
        TEST_PATH
    ),
)


updated_check_count = 0

for node in ast.walk(
    updated_tree
):
    if not isinstance(
        node,
        ast.Call,
    ):
        continue

    if not (
        isinstance(
            node.func,
            ast.Name,
        )
        and node.func.id == "check"
    ):
        continue

    if not node.args:
        continue

    first_argument = node.args[0]

    if (
        isinstance(
            first_argument,
            ast.Constant,
        )
        and first_argument.value
        == TARGET_CHECK_NAME
    ):
        updated_check_count += 1


if updated_check_count != 1:
    raise RuntimeError(
        "The repaired test does not contain exactly one "
        "Windows absolute-path acceptance check."
    )


required_markers = [
    "unsafe_windows_absolute_paths = {",
    'r"^[A-Za-z]:[\\\\/]"',
    "not unsafe_windows_absolute_paths",
]

for marker in required_markers:
    if marker not in updated_source:
        raise RuntimeError(
            "The repaired test is missing required marker: "
            f"{marker}"
        )


def is_windows_absolute_path(
    value: str,
) -> bool:
    cleaned_value = (
        value.strip()
        .strip('"')
        .strip("'")
    )

    return (
        re.match(
            r"^[A-Za-z]:[\\/]",
            cleaned_value,
        )
        is not None
    )


probe_expectations = {
    "http://127.0.0.1:8000": False,
    "http://127.0.0.1:8001": False,
    "http://127.0.0.1:8002": False,
    "sqlite:///./voice.db": False,
    "local": False,
    r"C:\private\voice.wav": True,
    "D:/private/voice.wav": True,
}


for value, expected in probe_expectations.items():
    actual = is_windows_absolute_path(
        value
    )

    if actual != expected:
        raise RuntimeError(
            "Windows-path detector probe failed.\n"
            f"Value: {value}\n"
            f"Expected: {expected}\n"
            f"Actual: {actual}"
        )


TEST_PATH.write_text(
    updated_source,
    encoding="utf-8",
)


print(
    "HTTP URL false-positive prevention: PASSED"
)

print(
    "Windows absolute-path detection: PASSED"
)

print(
    "Milestone 12.1B Windows-path acceptance check: REPAIRED"
)
