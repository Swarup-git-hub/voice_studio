from __future__ import annotations

import re
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]

TEST_PATH = (
    BACKEND_ROOT
    / "tests"
    / "test_milestone10_7d5e1_candidate_b_preflight.py"
)

source = TEST_PATH.read_text(
    encoding="utf-8-sig"
)

pattern = re.compile(
    r'''
    check\(
        \s*"Final\ call\ passes\ effective\ speed",
        .*?
    (?=
        \ncheck\(
        \s*"Final\ call\ passes\ effective\ volume",
    )
    ''',
    re.DOTALL | re.VERBOSE,
)

replacement = '''check(
    "Final call passes effective speed",
    (
        isinstance(
            final_keywords.get("speed"),
            ast.Name,
        )
        and final_keywords["speed"].id
        == "effective_speed"
    ),
    (
        ast.dump(
            final_keywords.get("speed")
        )
        if final_keywords.get("speed")
        is not None
        else "Missing"
    ),
)

'''

updated_source, replacement_count = pattern.subn(
    lambda _match: replacement,
    source,
    count=1,
)

if replacement_count != 1:
    raise RuntimeError(
        "Expected exactly one malformed effective-speed "
        "check block, but found "
        f"{replacement_count}."
    )

required_markers = [
    'final_keywords.get("speed")',
    'final_keywords["speed"].id',
    '== "effective_speed"',
    '"Final call passes effective volume"',
    '"Final call passes effective bass"',
    '"Final call forces speed processing"',
]

for marker in required_markers:
    if marker not in updated_source:
        raise RuntimeError(
            "Repaired test is missing required marker: "
            f"{marker}"
        )

TEST_PATH.write_text(
    updated_source,
    encoding="utf-8",
)

print(
    "Milestone 10.7D-5E-1 malformed "
    "preflight block: REPAIRED"
)
