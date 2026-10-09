from __future__ import annotations

import json
import re
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent

SOURCE_ENV_PATH = BACKEND_ROOT / ".env"
EXAMPLE_ENV_PATH = BACKEND_ROOT / ".env.example"
GITIGNORE_PATH = PROJECT_ROOT / ".gitignore"

MANAGED_BLOCK_START = (
    "# >>> AI VOICE STUDIO RELEASE HYGIENE >>>"
)

MANAGED_BLOCK_END = (
    "# <<< AI VOICE STUDIO RELEASE HYGIENE <<<"
)


checks_passed = 0


def check(
    name: str,
    condition: bool,
    detail: str = "",
) -> None:
    global checks_passed

    if not condition:
        message = f"{name}: FAILED"

        if detail:
            message += f"\n{detail}"

        raise AssertionError(
            message
        )

    checks_passed += 1
    print(
        f"{name}: PASSED"
    )


def parse_env(
    path: Path,
) -> list[tuple[str, str]]:
    assignments: list[
        tuple[str, str]
    ] = []

    for raw_line in path.read_text(
        encoding="utf-8-sig",
        errors="replace",
    ).splitlines():
        match = re.match(
            r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$",
            raw_line,
        )

        if match:
            assignments.append(
                (
                    match.group(
                        1
                    ),
                    match.group(
                        2
                    ).strip(),
                )
            )

    return assignments


def sensitive_key(
    key: str,
) -> bool:
    upper_key = key.upper()

    return any(
        marker in upper_key
        for marker in {
            "SECRET",
            "PASSWORD",
            "PASSCODE",
            "TOKEN",
            "API_KEY",
            "PRIVATE_KEY",
            "CREDENTIAL",
            "ACCESS_KEY",
            "AUTH_KEY",
            "CLIENT_SECRET",
            "COOKIE_KEY",
            "SESSION_KEY",
        }
    )


print("=" * 92)
print(
    "MILESTONE 12.1B — RELEASE HYGIENE "
    "STATIC ACCEPTANCE"
)
print("=" * 92)

check(
    "Private source environment exists",
    SOURCE_ENV_PATH.exists(),
    str(
        SOURCE_ENV_PATH
    ),
)

check(
    "Safe environment example exists",
    EXAMPLE_ENV_PATH.exists(),
    str(
        EXAMPLE_ENV_PATH
    ),
)

check(
    "Root gitignore exists",
    GITIGNORE_PATH.exists(),
    str(
        GITIGNORE_PATH
    ),
)

source_assignments = parse_env(
    SOURCE_ENV_PATH
)

example_assignments = parse_env(
    EXAMPLE_ENV_PATH
)

source_keys = [
    key
    for key, _value in source_assignments
]

example_keys = [
    key
    for key, _value in example_assignments
]

check(
    "Environment example contains all source keys",
    set(
        example_keys
    )
    == set(
        source_keys
    ),
    (
        f"Source keys: {source_keys}\n"
        f"Example keys: {example_keys}"
    ),
)

check(
    "Environment example contains no duplicate keys",
    len(
        example_keys
    )
    == len(
        set(
            example_keys
        )
    ),
)

example_values = dict(
    example_assignments
)

unsafe_sensitive_values = {
    key: example_values.get(
        key,
        ""
    )
    for key in source_keys
    if (
        sensitive_key(
            key
        )
        and example_values.get(
            key,
            ""
        )
    )
}

check(
    "Sensitive environment values remain blank",
    not unsafe_sensitive_values,
    repr(
        unsafe_sensitive_values
    ),
)

example_source = EXAMPLE_ENV_PATH.read_text(
    encoding="utf-8-sig",
    errors="replace",
)

unsafe_windows_absolute_paths = {
    key: value
    for key, value in example_assignments
    if re.match(
        r"^[A-Za-z]:[\\/]",
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

check(
    "Environment example explains safe local usage",
    (
        "contains no secrets"
        in example_source.lower()
        and "copy this file"
        in example_source.lower()
    ),
)

gitignore_source = GITIGNORE_PATH.read_text(
    encoding="utf-8-sig",
    errors="replace",
)

check(
    "Release-hygiene block appears exactly once",
    (
        gitignore_source.count(
            MANAGED_BLOCK_START
        )
        == 1
        and gitignore_source.count(
            MANAGED_BLOCK_END
        )
        == 1
    ),
)

expected_patterns = {
    "Root environment secret": "/.env",
    "Backend environment secret": "/backend/.env",
    "Backend environment example exception": (
        "!/backend/.env.example"
    ),
    "Root virtual environment": "/.venv/",
    "IndicF5 virtual environment": "/indicf5_env/",
    "CosyVoice virtual environment": "/cosyvoice_env/",
    "Manager state files": (
        "/.ai_voice_studio_state*.json"
    ),
    "Local service logs": "/logs/",
    "Saved reference voices": (
        "/backend/app/voices/"
    ),
    "Generated audio": (
        "/backend/app/outputs/"
    ),
    "SQLite database": (
        "/backend/voice.db"
    ),
    "Frontend dependencies": (
        "/frontend/node_modules/"
    ),
    "Frontend production bundle": (
        "/frontend/dist/"
    ),
    "Milestone backups": (
        "/backend/milestone_backups/"
    ),
    "Milestone reports": (
        "/backend/milestone_reports/"
    ),
}

for name, pattern in expected_patterns.items():
    check(
        name,
        pattern in gitignore_source,
        pattern,
    )

check(
    "Environment example exception follows secret rules",
    (
        gitignore_source.index(
            "/backend/.env.*"
        )
        < gitignore_source.index(
            "!/backend/.env.example"
        )
    ),
)

report_candidates = sorted(
    (
        BACKEND_ROOT
        / "milestone_reports"
    ).glob(
        "milestone12_1b_release_hygiene_*.json"
    ),
    key=lambda path: path.stat().st_mtime,
    reverse=True,
)

check(
    "Implementation report exists",
    bool(
        report_candidates
    ),
)

report_path = report_candidates[0]

report = json.loads(
    report_path.read_text(
        encoding="utf-8"
    )
)

check(
    "Runtime data remained unchanged",
    (
        report[
            "runtime_snapshot_before"
        ]
        == report[
            "runtime_snapshot_after"
        ]
        and not report[
            "runtime_data_modified"
        ]
    ),
)

check(
    "Implementation report contains no environment values",
    report.get(
        "environment_values_recorded"
    )
    is False,
)

print()
print("=" * 92)
print(
    "MILESTONE 12.1B RELEASE HYGIENE "
    "STATIC ACCEPTANCE: PASSED"
)
print("=" * 92)

print(
    "Checks passed:",
    checks_passed,
)

print(
    "Application source files modified: NO"
)

print(
    "Private runtime data modified: NO"
)

print(
    "Services started: NO"
)

print()
print(
    "Environment example:",
    EXAMPLE_ENV_PATH,
)

print(
    "Gitignore:",
    GITIGNORE_PATH,
)

print(
    "Report:",
    report_path,
)
