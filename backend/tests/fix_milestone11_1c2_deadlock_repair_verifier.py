from __future__ import annotations

from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]

REPAIR_PATH = (
    BACKEND_ROOT
    / "tests"
    / "repair_milestone11_1c2_manager_output_deadlock.py"
)

source = REPAIR_PATH.read_text(
    encoding="utf-8-sig"
)

old_snippet = '''                termination = subprocess.run(
                    [
                        "taskkill.exe",
                        "/PID",
                        str(
                            process.pid
                        ),
                        "/T",
                        "/F",
                    ],
                    capture_output=True,
                    text=True,
                    errors="replace",
                    check=False,
                )
'''

new_snippet = '''                termination = subprocess.run(
                    [
                        "taskkill.exe",
                        "/PID",
                        str(
                            process.pid
                        ),
                        "/T",
                        "/F",
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    errors="replace",
                    check=False,
                )
'''

old_count = source.count(
    old_snippet
)

if old_count != 1:
    raise RuntimeError(
        "Expected exactly one taskkill capture block, "
        f"found {old_count}."
    )

updated_source = source.replace(
    old_snippet,
    new_snippet,
    1,
)

required_markers = [
    "stdout=subprocess.PIPE",
    "stderr=subprocess.PIPE",
    "termination.stdout",
    "termination.stderr",
    'for forbidden_marker in [',
    '"capture_output=True"',
]

for marker in required_markers:
    if marker not in updated_source:
        raise RuntimeError(
            "Corrected repair script is missing marker: "
            f"{marker}"
        )

if old_snippet in updated_source:
    raise RuntimeError(
        "The rejected taskkill capture block remains."
    )

REPAIR_PATH.write_text(
    updated_source,
    encoding="utf-8",
)

print(
    "Milestone 11.1C-2 deadlock-repair "
    "verifier conflict: FIXED"
)
