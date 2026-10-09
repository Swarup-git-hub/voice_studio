from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
FRONTEND_ROOT = PROJECT_ROOT / "frontend"

REPORT_PATH = (
    BACKEND_ROOT
    / "milestone_reports"
    / "milestone12_1a_local_release_preflight.json"
)

TEXT_REPORT_PATH = (
    BACKEND_ROOT
    / "milestone_reports"
    / "milestone12_1a_local_release_preflight.txt"
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


def command_version(
    command: list[str],
) -> str | None:
    try:
        completed = subprocess.run(
            command,
            cwd=str(
                PROJECT_ROOT
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )

    except (
        OSError,
        subprocess.TimeoutExpired,
    ):
        return None

    output = (
        completed.stdout.strip()
        or completed.stderr.strip()
    )

    return output or None


def directory_stats(
    directory: Path,
) -> dict[str, Any]:
    if not directory.exists():
        return {
            "exists": False,
            "file_count": 0,
            "total_bytes": 0,
        }

    file_count = 0
    total_bytes = 0

    for root, _directories, files in os.walk(
        directory
    ):
        root_path = Path(
            root
        )

        for filename in files:
            path = (
                root_path
                / filename
            )

            try:
                file_count += 1
                total_bytes += path.stat().st_size

            except OSError:
                continue

    return {
        "exists": True,
        "file_count": file_count,
        "total_bytes": total_bytes,
    }


def extract_env_keys(
    env_path: Path,
) -> list[str]:
    if not env_path.exists():
        return []

    keys: list[str] = []

    for raw_line in env_path.read_text(
        encoding="utf-8-sig",
        errors="replace",
    ).splitlines():
        line = raw_line.strip()

        if (
            not line
            or line.startswith("#")
            or "=" not in line
        ):
            continue

        key = line.split(
            "=",
            maxsplit=1,
        )[0].strip()

        if re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*",
            key,
        ):
            keys.append(
                key
            )

    return sorted(
        set(
            keys
        )
    )


def ignore_marker_present(
    gitignore_source: str,
    alternatives: list[str],
) -> bool:
    normalized_lines = [
        line.strip()
        .replace(
            "\\",
            "/",
        )
        .lower()
        for line in gitignore_source.splitlines()
        if (
            line.strip()
            and not line.strip().startswith("#")
        )
    ]

    for alternative in alternatives:
        normalized_alternative = (
            alternative
            .replace(
                "\\",
                "/",
            )
            .lower()
        )

        if any(
            normalized_alternative in line
            for line in normalized_lines
        ):
            return True

    return False


def format_bytes(
    size: int,
) -> str:
    units = [
        "B",
        "KB",
        "MB",
        "GB",
    ]

    value = float(
        size
    )

    unit = units[0]

    for candidate in units:
        unit = candidate

        if (
            value < 1024
            or candidate == units[-1]
        ):
            break

        value /= 1024

    return f"{value:.2f} {unit}"


print("=" * 92)
print(
    "MILESTONE 12.1A — LOCAL RELEASE "
    "READINESS INVENTORY"
)
print("=" * 92)

required_project_paths = {
    "Project root": PROJECT_ROOT,
    "Backend root": BACKEND_ROOT,
    "Frontend root": FRONTEND_ROOT,
    "Startup manager": (
        PROJECT_ROOT
        / "start_ai_voice_studio.ps1"
    ),
    "Stop manager": (
        PROJECT_ROOT
        / "stop_ai_voice_studio.ps1"
    ),
    "Backend entry point": (
        BACKEND_ROOT
        / "app"
        / "main.py"
    ),
    "Backend requirements": (
        BACKEND_ROOT
        / "requirements.txt"
    ),
    "Frontend package manifest": (
        FRONTEND_ROOT
        / "package.json"
    ),
    "Frontend source": (
        FRONTEND_ROOT
        / "src"
    ),
    "CosyVoice service": (
        BACKEND_ROOT
        / "ai_models"
        / "cosyvoice"
        / "server.py"
    ),
    "IndicF5 service": (
        BACKEND_ROOT
        / "ai_models"
        / "indicf5"
        / "server.py"
    ),
}

for name, path in required_project_paths.items():
    check(
        name,
        path.exists(),
        str(
            path
        ),
    )


package_path = (
    FRONTEND_ROOT
    / "package.json"
)

package_data = json.loads(
    package_path.read_text(
        encoding="utf-8-sig"
    )
)

frontend_scripts = package_data.get(
    "scripts",
    {},
)

check(
    "Frontend development script exists",
    "dev"
    in frontend_scripts,
)

check(
    "Frontend production build script exists",
    "build"
    in frontend_scripts,
)

check(
    "Frontend lint script exists",
    "lint"
    in frontend_scripts,
)


root_python = (
    PROJECT_ROOT
    / ".venv"
    / "Scripts"
    / "python.exe"
)

indic_python = (
    PROJECT_ROOT
    / "indicf5_env"
    / "Scripts"
    / "python.exe"
)

cosyvoice_python = (
    PROJECT_ROOT
    / "cosyvoice_env"
    / "Scripts"
    / "python.exe"
)

environment_versions = {
    "root_python": (
        command_version(
            [
                str(
                    root_python
                ),
                "--version",
            ]
        )
        if root_python.exists()
        else None
    ),
    "indicf5_python": (
        command_version(
            [
                str(
                    indic_python
                ),
                "--version",
            ]
        )
        if indic_python.exists()
        else None
    ),
    "cosyvoice_python": (
        command_version(
            [
                str(
                    cosyvoice_python
                ),
                "--version",
            ]
        )
        if cosyvoice_python.exists()
        else None
    ),
    "node": (
        command_version(
            [
                shutil.which(
                    "node"
                )
                or "node",
                "--version",
            ]
        )
    ),
    "npm": (
        command_version(
            [
                shutil.which(
                    "npm.cmd"
                )
                or "npm.cmd",
                "--version",
            ]
        )
    ),
    "ffmpeg": (
        command_version(
            [
                shutil.which(
                    "ffmpeg"
                )
                or "ffmpeg",
                "-version",
            ]
        )
    ),
}


release_document_candidates = {
    "README": [
        PROJECT_ROOT
        / "README.md",
        BACKEND_ROOT
        / "README.md",
    ],
    "Environment example": [
        PROJECT_ROOT
        / ".env.example",
        BACKEND_ROOT
        / ".env.example",
    ],
    "Git ignore rules": [
        PROJECT_ROOT
        / ".gitignore",
    ],
    "Licence": [
        PROJECT_ROOT
        / "LICENSE",
        PROJECT_ROOT
        / "LICENSE.md",
    ],
    "Voice-use and consent policy": [
        PROJECT_ROOT
        / "VOICE_USE_POLICY.md",
        PROJECT_ROOT
        / "VOICE_CONSENT.md",
    ],
    "Security guidance": [
        PROJECT_ROOT
        / "SECURITY.md",
    ],
    "Changelog": [
        PROJECT_ROOT
        / "CHANGELOG.md",
    ],
}

release_documents: dict[
    str,
    dict[str, Any]
] = {}

for name, candidates in release_document_candidates.items():
    existing_paths = [
        str(
            path
        )
        for path in candidates
        if path.exists()
    ]

    release_documents[name] = {
        "present": bool(
            existing_paths
        ),
        "existing_paths": existing_paths,
        "candidate_paths": [
            str(
                path
            )
            for path in candidates
        ],
    }


env_paths = [
    PROJECT_ROOT
    / ".env",
    BACKEND_ROOT
    / ".env",
]

existing_env_paths = [
    path
    for path in env_paths
    if path.exists()
]

env_files = [
    {
        "path": str(
            path
        ),
        "keys": extract_env_keys(
            path
        ),
        "values_recorded": False,
    }
    for path in existing_env_paths
]


gitignore_path = (
    PROJECT_ROOT
    / ".gitignore"
)

gitignore_source = (
    gitignore_path.read_text(
        encoding="utf-8-sig",
        errors="replace",
    )
    if gitignore_path.exists()
    else ""
)

ignore_requirements = {
    "Environment secrets": [
        ".env",
    ],
    "Root virtual environment": [
        ".venv",
    ],
    "IndicF5 virtual environment": [
        "indicf5_env",
    ],
    "CosyVoice virtual environment": [
        "cosyvoice_env",
    ],
    "Manager state files": [
        ".ai_voice_studio_state",
    ],
    "Service logs": [
        "logs/",
        "logs",
    ],
    "Generated audio": [
        "outputs/",
        "app/outputs",
    ],
    "Saved reference voices": [
        "voices/",
        "app/voices",
    ],
    "SQLite database": [
        "*.db",
        "voice.db",
    ],
    "Python cache": [
        "__pycache__",
        "*.pyc",
    ],
    "Frontend dependencies": [
        "node_modules",
    ],
    "Frontend production bundle": [
        "dist/",
        "dist",
    ],
}

ignore_coverage = {
    name: ignore_marker_present(
        gitignore_source,
        markers,
    )
    for name, markers in ignore_requirements.items()
}


runtime_directories = {
    "Backend generated outputs": (
        BACKEND_ROOT
        / "app"
        / "outputs"
    ),
    "Backend saved voices": (
        BACKEND_ROOT
        / "app"
        / "voices"
    ),
    "Local service logs": (
        PROJECT_ROOT
        / "logs"
    ),
    "Milestone backups": (
        BACKEND_ROOT
        / "milestone_backups"
    ),
    "Milestone reports": (
        BACKEND_ROOT
        / "milestone_reports"
    ),
    "Frontend node_modules": (
        FRONTEND_ROOT
        / "node_modules"
    ),
    "Frontend dist": (
        FRONTEND_ROOT
        / "dist"
    ),
}

runtime_inventory = {
    name: directory_stats(
        path
    )
    | {
        "path": str(
            path
        )
    }
    for name, path in runtime_directories.items()
}


database_candidates = [
    BACKEND_ROOT
    / "voice.db",
    PROJECT_ROOT
    / "voice.db",
]

database_inventory = [
    {
        "path": str(
            path
        ),
        "size_bytes": path.stat().st_size,
    }
    for path in database_candidates
    if path.exists()
]


start_script_path = (
    PROJECT_ROOT
    / "start_ai_voice_studio.ps1"
)

start_script_source = start_script_path.read_text(
    encoding="utf-8-sig",
    errors="replace",
)

detected_ports = sorted(
    {
        int(
            value
        )
        for value in re.findall(
            r"\b(?:5173|8000|8001|8002)\b",
            start_script_source,
        )
    }
)


recommended_actions: list[str] = []

if not release_documents[
    "README"
][
    "present"
]:
    recommended_actions.append(
        "Create a root README.md with architecture, setup, "
        "startup, shutdown, usage and troubleshooting instructions."
    )

if not release_documents[
    "Environment example"
][
    "present"
]:
    recommended_actions.append(
        "Create a safe .env.example containing variable names "
        "and non-secret example values."
    )

if not release_documents[
    "Git ignore rules"
][
    "present"
]:
    recommended_actions.append(
        "Create a root .gitignore before making a release archive "
        "or publishing the repository."
    )

missing_ignore_coverage = [
    name
    for name, covered in ignore_coverage.items()
    if not covered
]

if missing_ignore_coverage:
    recommended_actions.append(
        "Add missing .gitignore coverage for: "
        + ", ".join(
            missing_ignore_coverage
        )
        + "."
    )

if not release_documents[
    "Licence"
][
    "present"
]:
    recommended_actions.append(
        "Choose and add a software licence before public release."
    )

if not release_documents[
    "Voice-use and consent policy"
][
    "present"
]:
    recommended_actions.append(
        "Add a voice-use and consent policy explaining that only "
        "authorised reference voices may be uploaded or cloned."
    )

if not release_documents[
    "Security guidance"
][
    "present"
]:
    recommended_actions.append(
        "Add SECURITY.md covering voice-data protection, local "
        "storage and responsible vulnerability reporting."
    )

if database_inventory:
    recommended_actions.append(
        "Exclude the populated SQLite database from release assets "
        "and initialise a clean database at first launch."
    )

if runtime_inventory[
    "Backend generated outputs"
][
    "file_count"
] > 0:
    recommended_actions.append(
        "Exclude generated audio history and WAV outputs from the "
        "release package."
    )

if runtime_inventory[
    "Backend saved voices"
][
    "file_count"
] > 0:
    recommended_actions.append(
        "Exclude personal reference-voice recordings from the "
        "release package."
    )

recommended_actions.append(
    "Document the three Python environments and the required "
    "Node.js, FFmpeg and NVIDIA/CUDA prerequisites."
)

recommended_actions.append(
    "Create a deterministic local-release validation command "
    "that verifies installation without loading personal data."
)


report: dict[str, Any] = {
    "milestone": "12.1A",
    "created_at": datetime.now().isoformat(),
    "mode": "read-only application inventory",
    "application_files_modified": False,
    "checks_passed": checks_passed,
    "project_root": str(
        PROJECT_ROOT
    ),
    "required_project_paths": {
        name: {
            "path": str(
                path
            ),
            "exists": path.exists(),
        }
        for name, path in required_project_paths.items()
    },
    "frontend": {
        "package_name": package_data.get(
            "name"
        ),
        "package_version": package_data.get(
            "version"
        ),
        "scripts": frontend_scripts,
        "package_lock_exists": (
            FRONTEND_ROOT
            / "package-lock.json"
        ).exists(),
    },
    "environment_versions": environment_versions,
    "release_documents": release_documents,
    "environment_files": env_files,
    "environment_values_recorded": False,
    "gitignore": {
        "path": str(
            gitignore_path
        ),
        "exists": gitignore_path.exists(),
        "coverage": ignore_coverage,
        "missing_coverage": missing_ignore_coverage,
    },
    "runtime_inventory": runtime_inventory,
    "database_inventory": database_inventory,
    "startup_ports_detected": detected_ports,
    "recommended_actions": recommended_actions,
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


text_lines: list[str] = [
    "=" * 92,
    "MILESTONE 12.1A — LOCAL RELEASE READINESS INVENTORY",
    "=" * 92,
    "",
    "ENVIRONMENT VERSIONS",
    "-" * 92,
]

for name, version in environment_versions.items():
    text_lines.append(
        f"{name:24}: {version or 'NOT FOUND'}"
    )

text_lines.extend(
    [
        "",
        "RELEASE DOCUMENTS",
        "-" * 92,
    ]
)

for name, details in release_documents.items():
    text_lines.append(
        f"{name:30}: "
        f"{'PRESENT' if details['present'] else 'MISSING'}"
    )

text_lines.extend(
    [
        "",
        "GITIGNORE COVERAGE",
        "-" * 92,
    ]
)

for name, covered in ignore_coverage.items():
    text_lines.append(
        f"{name:30}: "
        f"{'COVERED' if covered else 'MISSING'}"
    )

text_lines.extend(
    [
        "",
        "RUNTIME DATA INVENTORY",
        "-" * 92,
    ]
)

for name, details in runtime_inventory.items():
    text_lines.append(
        f"{name:30}: "
        f"{details['file_count']} files, "
        f"{format_bytes(details['total_bytes'])}"
    )

text_lines.extend(
    [
        "",
        "RECOMMENDED RELEASE ACTIONS",
        "-" * 92,
    ]
)

for index, action in enumerate(
    recommended_actions,
    start=1,
):
    text_lines.append(
        f"{index}. {action}"
    )

text_lines.extend(
    [
        "",
        "=" * 92,
        "MILESTONE 12.1A LOCAL RELEASE READINESS INVENTORY: COMPLETE",
        "=" * 92,
        f"Checks passed: {checks_passed}",
        "Application files modified: NO",
        "",
        f"JSON report: {REPORT_PATH}",
        f"Text report: {TEXT_REPORT_PATH}",
    ]
)

TEXT_REPORT_PATH.write_text(
    "\n".join(
        text_lines
    )
    + "\n",
    encoding="utf-8",
)

print()
print(
    "\n".join(
        text_lines
    )
)
