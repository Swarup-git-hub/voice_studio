from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent

SOURCE_ENV_PATH = BACKEND_ROOT / ".env"
EXAMPLE_ENV_PATH = BACKEND_ROOT / ".env.example"
GITIGNORE_PATH = PROJECT_ROOT / ".gitignore"

REPORT_PATH = Path(
    os.environ[
        "MILESTONE12_1B_REPORT_PATH"
    ]
).resolve()

MANAGED_BLOCK_START = (
    "# >>> AI VOICE STUDIO RELEASE HYGIENE >>>"
)

MANAGED_BLOCK_END = (
    "# <<< AI VOICE STUDIO RELEASE HYGIENE <<<"
)


def runtime_snapshot() -> dict[str, Any]:
    tracked_directories = {
        "outputs": (
            BACKEND_ROOT
            / "app"
            / "outputs"
        ),
        "voices": (
            BACKEND_ROOT
            / "app"
            / "voices"
        ),
        "logs": (
            PROJECT_ROOT
            / "logs"
        ),
    }

    snapshot: dict[str, Any] = {}

    for name, directory in tracked_directories.items():
        file_count = 0
        total_bytes = 0

        if directory.exists():
            for path in directory.rglob(
                "*"
            ):
                if not path.is_file():
                    continue

                try:
                    file_count += 1
                    total_bytes += path.stat().st_size

                except OSError:
                    continue

        snapshot[
            name
        ] = {
            "path": str(
                directory
            ),
            "file_count": file_count,
            "total_bytes": total_bytes,
        }

    database_path = (
        BACKEND_ROOT
        / "voice.db"
    )

    snapshot[
        "database"
    ] = {
        "path": str(
            database_path
        ),
        "exists": database_path.exists(),
        "size_bytes": (
            database_path.stat().st_size
            if database_path.exists()
            else 0
        ),
    }

    return snapshot


def parse_env_assignments(
    path: Path,
) -> list[tuple[str, str]]:
    assignments: list[
        tuple[str, str]
    ] = []

    seen_keys: set[str] = set()

    for raw_line in path.read_text(
        encoding="utf-8-sig",
        errors="replace",
    ).splitlines():
        match = re.match(
            r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$",
            raw_line,
        )

        if not match:
            continue

        key = match.group(
            1
        )

        raw_value = match.group(
            2
        ).strip()

        if key in seen_keys:
            raise RuntimeError(
                "Duplicate environment key found in "
                f"{path}: {key}"
            )

        seen_keys.add(
            key
        )

        assignments.append(
            (
                key,
                raw_value,
            )
        )

    if not assignments:
        raise RuntimeError(
            f"No environment variables were found in {path}."
        )

    return assignments


def unquote(
    value: str,
) -> str:
    if (
        len(
            value
        )
        >= 2
        and value[0] == value[-1]
        and value[0] in {
            '"',
            "'",
        }
    ):
        return value[
            1:-1
        ]

    return value


def is_sensitive_key(
    key: str,
) -> bool:
    upper_key = key.upper()

    sensitive_markers = {
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

    return any(
        marker in upper_key
        for marker in sensitive_markers
    )


def safe_example_value(
    key: str,
    raw_value: str,
) -> str:
    upper_key = key.upper()

    plain_value = unquote(
        raw_value
    ).strip()

    if is_sensitive_key(
        key
    ):
        return ""

    if upper_key == "DATABASE_URL":
        return "sqlite:///./voice.db"

    if (
        "CORS" in upper_key
        or "ORIGIN" in upper_key
        or "FRONTEND_URL" in upper_key
    ):
        if plain_value.startswith(
            "["
        ):
            return (
                '["http://127.0.0.1:5173"]'
            )

        return "http://127.0.0.1:5173"

    if (
        "COSY" in upper_key
        and (
            "URL" in upper_key
            or "ENDPOINT" in upper_key
        )
    ):
        return "http://127.0.0.1:8001"

    if (
        (
            "INDIC" in upper_key
            or "F5" in upper_key
        )
        and (
            "URL" in upper_key
            or "ENDPOINT" in upper_key
        )
    ):
        return "http://127.0.0.1:8002"

    if (
        "BACKEND_URL" in upper_key
        or "API_URL" in upper_key
    ):
        return "http://127.0.0.1:8000"

    if upper_key.endswith(
        "HOST"
    ):
        return "127.0.0.1"

    if upper_key.endswith(
        "PORT"
    ):
        if "FRONTEND" in upper_key:
            return "5173"

        if "COSY" in upper_key:
            return "8001"

        if (
            "INDIC" in upper_key
            or "F5" in upper_key
        ):
            return "8002"

        return "8000"

    if upper_key in {
        "APP_NAME",
        "APPLICATION_NAME",
    }:
        return '"AI Voice Studio"'

    if upper_key in {
        "APP_VERSION",
        "VERSION",
    }:
        if re.fullmatch(
            r"\d+(?:\.\d+){1,3}",
            plain_value,
        ):
            return plain_value

        return "1.0.0"

    if upper_key in {
        "ENVIRONMENT",
        "APP_ENV",
    }:
        return "local"

    if plain_value.lower() in {
        "true",
        "false",
    }:
        return plain_value.lower()

    numeric_key_markers = {
        "TIMEOUT",
        "WORKERS",
        "RETRIES",
        "SAMPLE_RATE",
        "MAX_",
        "MIN_",
        "LIMIT",
    }

    if (
        re.fullmatch(
            r"-?\d+(?:\.\d+)?",
            plain_value,
        )
        and any(
            marker in upper_key
            for marker in numeric_key_markers
        )
    ):
        return plain_value

    safe_named_value_keys = {
        "DEVICE",
        "LOG_LEVEL",
        "WHISPER_MODEL",
        "MODEL_NAME",
        "MODEL_SIZE",
        "DEFAULT_ENGINE",
    }

    if (
        upper_key in safe_named_value_keys
        and re.fullmatch(
            r"[A-Za-z0-9_.-]+",
            plain_value,
        )
    ):
        return plain_value

    # Unknown values remain intentionally blank so no personal path,
    # identifier, token or machine-specific setting is copied.
    return ""


before_snapshot = runtime_snapshot()

assignments = parse_env_assignments(
    SOURCE_ENV_PATH
)

example_lines = [
    "# AI Voice Studio local environment template",
    "#",
    "# Copy this file to backend/.env before first launch.",
    "# Review every blank value for your own machine.",
    "# This template contains no secrets or personal absolute paths.",
    "",
]

example_values: dict[
    str,
    str
] = {}

for key, raw_value in assignments:
    safe_value = safe_example_value(
        key,
        raw_value,
    )

    example_values[
        key
    ] = safe_value

    example_lines.append(
        f"{key}={safe_value}"
    )

EXAMPLE_ENV_PATH.write_text(
    "\n".join(
        example_lines
    )
    + "\n",
    encoding="utf-8",
)


managed_block = """# >>> AI VOICE STUDIO RELEASE HYGIENE >>>
# Local environment files and secrets
/.env
/.env.*
!/.env.example
/backend/.env
/backend/.env.*
!/backend/.env.example

# Local Python environments
/.venv/
/indicf5_env/
/cosyvoice_env/

# Startup-manager state and local logs
/.ai_voice_studio_state*.json
/logs/

# Private reference voices, generated audio and databases
/backend/app/voices/
/backend/app/outputs/
/backend/voice.db
/backend/*.db

# Frontend dependencies and production output
/frontend/node_modules/
/frontend/dist/
/frontend/.vite/

# Python runtime caches
**/__pycache__/
*.py[cod]

# Internal milestone workspaces and reports
/backend/milestone_backups/
/backend/milestone_reports/
/backend/tests/.milestone*/

# Operating-system temporary files
.DS_Store
Thumbs.db
# <<< AI VOICE STUDIO RELEASE HYGIENE <<<"""


gitignore_source = GITIGNORE_PATH.read_text(
    encoding="utf-8-sig",
    errors="replace",
)

existing_block_pattern = re.compile(
    re.escape(
        MANAGED_BLOCK_START
    )
    + r".*?"
    + re.escape(
        MANAGED_BLOCK_END
    ),
    flags=re.DOTALL,
)

gitignore_without_block = (
    existing_block_pattern.sub(
        "",
        gitignore_source,
    )
    .rstrip()
)

updated_gitignore = (
    gitignore_without_block
    + "\n\n"
    + managed_block
    + "\n"
)

GITIGNORE_PATH.write_text(
    updated_gitignore,
    encoding="utf-8",
)

after_snapshot = runtime_snapshot()

if before_snapshot != after_snapshot:
    raise RuntimeError(
        "Runtime data changed during release-hygiene "
        "implementation."
    )

sensitive_keys = [
    key
    for key, _raw_value in assignments
    if is_sensitive_key(
        key
    )
]

report = {
    "milestone": "12.1B",
    "created_at": datetime.now().isoformat(),
    "application_source_files_modified": False,
    "release_files_modified": [
        str(
            EXAMPLE_ENV_PATH
        ),
        str(
            GITIGNORE_PATH
        ),
    ],
    "source_environment_path": str(
        SOURCE_ENV_PATH
    ),
    "environment_example_path": str(
        EXAMPLE_ENV_PATH
    ),
    "environment_key_count": len(
        assignments
    ),
    "environment_keys": [
        key
        for key, _raw_value in assignments
    ],
    "sensitive_keys_blank": sensitive_keys,
    "environment_values_recorded": False,
    "gitignore_managed_block": {
        "start": MANAGED_BLOCK_START,
        "end": MANAGED_BLOCK_END,
    },
    "runtime_snapshot_before": before_snapshot,
    "runtime_snapshot_after": after_snapshot,
    "runtime_data_modified": False,
}

REPORT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

REPORT_PATH.write_text(
    json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)

print(
    "Environment source:",
    SOURCE_ENV_PATH,
)

print(
    "Environment example:",
    EXAMPLE_ENV_PATH,
)

print(
    "Environment keys included:",
    len(
        assignments
    ),
)

print(
    "Sensitive values copied: NO"
)

print(
    "Personal absolute paths copied: NO"
)

print(
    "Gitignore managed block: APPLIED"
)

print(
    "Runtime data modified: NO"
)

print(
    "Implementation report:",
    REPORT_PATH,
)

print(
    "Milestone 12.1B release-hygiene "
    "implementation: APPLIED"
)
