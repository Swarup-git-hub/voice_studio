from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(
    os.environ[
        "MILESTONE12_2A_PROJECT_ROOT"
    ]
).resolve()

BACKEND_ROOT = (
    PROJECT_ROOT
    / "backend"
)

FRONTEND_ROOT = (
    PROJECT_ROOT
    / "frontend"
)

ROOT_PYTHON = Path(
    os.environ[
        "MILESTONE12_2A_ROOT_PYTHON"
    ]
).resolve()

INDIC_PYTHON = Path(
    os.environ[
        "MILESTONE12_2A_INDIC_PYTHON"
    ]
).resolve()

COSY_PYTHON = Path(
    os.environ[
        "MILESTONE12_2A_COSY_PYTHON"
    ]
).resolve()

JSON_REPORT_PATH = Path(
    os.environ[
        "MILESTONE12_2A_JSON_REPORT"
    ]
).resolve()

TEXT_REPORT_PATH = Path(
    os.environ[
        "MILESTONE12_2A_TEXT_REPORT"
    ]
).resolve()


REQUIREMENTS_PATH = (
    BACKEND_ROOT
    / "requirements.txt"
)

PACKAGE_JSON_PATH = (
    FRONTEND_ROOT
    / "package.json"
)

NODE_MODULES_ROOT = (
    FRONTEND_ROOT
    / "node_modules"
)

COSYVOICE_ROOT = (
    BACKEND_ROOT
    / "ai_models"
    / "cosyvoice"
)

INDICF5_ROOT = (
    BACKEND_ROOT
    / "ai_models"
    / "indicf5"
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


def normalise_package_name(
    name: str,
) -> str:
    return re.sub(
        r"[-_.]+",
        "-",
        name,
    ).lower()


def run_command(
    command: list[str],
    *,
    working_directory: Path,
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=str(
                working_directory
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )

    except (
        OSError,
        subprocess.TimeoutExpired,
    ) as error:
        return {
            "success": False,
            "return_code": None,
            "stdout": "",
            "stderr": (
                f"{type(error).__name__}: {error}"
            ),
        }

    return {
        "success": completed.returncode == 0,
        "return_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


PACKAGE_METADATA_HELPER = r'''
from __future__ import annotations

import importlib.metadata as metadata
import json
import sys


packages = []

for distribution in metadata.distributions():
    package_metadata = distribution.metadata

    name = (
        package_metadata.get("Name")
        or distribution.name
        or "UNKNOWN"
    )

    version = (
        distribution.version
        or ""
    )

    licence_value = (
        package_metadata.get("License")
        or ""
    ).strip()

    classifiers = (
        package_metadata.get_all(
            "Classifier"
        )
        or []
    )

    licence_classifiers = [
        classifier
        for classifier in classifiers
        if classifier.startswith(
            "License ::"
        )
    ]

    project_urls = {}

    for project_url in (
        package_metadata.get_all(
            "Project-URL"
        )
        or []
    ):
        if "," not in project_url:
            continue

        label, value = project_url.split(
            ",",
            maxsplit=1,
        )

        project_urls[
            label.strip()
        ] = value.strip()

    packages.append(
        {
            "name": name,
            "version": version,
            "license": licence_value,
            "license_classifiers": licence_classifiers,
            "home_page": (
                package_metadata.get(
                    "Home-page"
                )
                or ""
            ),
            "project_urls": project_urls,
        }
    )


packages.sort(
    key=lambda item: item[
        "name"
    ].lower()
)


print(
    json.dumps(
        {
            "python_version": sys.version,
            "executable": sys.executable,
            "package_count": len(
                packages
            ),
            "packages": packages,
        },
        ensure_ascii=False,
    )
)
'''


def inventory_python_environment(
    name: str,
    python_path: Path,
) -> dict[str, Any]:
    result = run_command(
        [
            str(
                python_path
            ),
            "-X",
            "utf8",
            "-c",
            PACKAGE_METADATA_HELPER,
        ],
        working_directory=BACKEND_ROOT,
        timeout_seconds=180,
    )

    if not result[
        "success"
    ]:
        raise RuntimeError(
            f"Could not inventory {name}.\n"
            f"Executable: {python_path}\n"
            f"Standard error:\n{result['stderr']}"
        )

    try:
        payload = json.loads(
            result[
                "stdout"
            ]
        )

    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"Invalid metadata JSON from {name}.\n"
            f"{error}\n"
            f"Output:\n{result['stdout'][:2000]}"
        ) from error

    payload[
        "environment_name"
    ] = name

    return payload


def read_requirements(
    path: Path,
) -> dict[str, Any]:
    raw_entries: list[str] = []
    named_requirements: list[
        dict[str, str]
    ] = []
    unresolved_entries: list[str] = []

    for raw_line in path.read_text(
        encoding="utf-8-sig",
        errors="replace",
    ).splitlines():
        line = raw_line.strip()

        if (
            not line
            or line.startswith("#")
        ):
            continue

        raw_entries.append(
            line
        )

        if (
            line.startswith("-")
            or line.startswith("git+")
            or line.startswith("http://")
            or line.startswith("https://")
            or line.startswith(".")
        ):
            unresolved_entries.append(
                line
            )
            continue

        match = re.match(
            r"^([A-Za-z0-9_.-]+)",
            line,
        )

        if not match:
            unresolved_entries.append(
                line
            )
            continue

        package_name = match.group(
            1
        )

        named_requirements.append(
            {
                "raw": line,
                "name": package_name,
                "normalised_name": (
                    normalise_package_name(
                        package_name
                    )
                ),
            }
        )

    return {
        "path": str(
            path
        ),
        "raw_entry_count": len(
            raw_entries
        ),
        "raw_entries": raw_entries,
        "named_requirements": named_requirements,
        "unresolved_entries": unresolved_entries,
    }


def classify_licence_record(
    licence_value: str,
    classifiers: list[str],
) -> list[str]:
    combined = " ".join(
        [
            licence_value,
            *classifiers,
        ]
    ).lower()

    flags: list[str] = []

    if not combined.strip():
        flags.append(
            "missing-licence-metadata"
        )

    if combined.strip() in {
        "unknown",
        "none",
        "n/a",
    }:
        flags.append(
            "unclear-licence-metadata"
        )

    review_markers = {
        "agpl": "agpl-review",
        "gnu affero": "agpl-review",
        "gpl": "gpl-review",
        "general public license": "gpl-review",
        "lgpl": "lgpl-review",
        "lesser general public": "lgpl-review",
        "non-commercial": "non-commercial-review",
        "noncommercial": "non-commercial-review",
        "proprietary": "proprietary-review",
        "commercial license": "commercial-terms-review",
        "custom": "custom-licence-review",
        "licenseref": "custom-licence-review",
    }

    for marker, flag in review_markers.items():
        if (
            marker in combined
            and flag not in flags
        ):
            flags.append(
                flag
            )

    return flags


def index_environment_packages(
    environment: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        normalise_package_name(
            package[
                "name"
            ]
        ): package
        for package in environment[
            "packages"
        ]
    }


def match_direct_requirements(
    requirements: dict[str, Any],
    environments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    environment_indexes = {
        environment[
            "environment_name"
        ]: index_environment_packages(
            environment
        )
        for environment in environments
    }

    matches: list[
        dict[str, Any]
    ] = []

    for requirement in requirements[
        "named_requirements"
    ]:
        environment_matches = {}

        for environment_name, package_index in (
            environment_indexes.items()
        ):
            package = package_index.get(
                requirement[
                    "normalised_name"
                ]
            )

            if package is None:
                environment_matches[
                    environment_name
                ] = None

                continue

            flags = classify_licence_record(
                package.get(
                    "license",
                    "",
                ),
                package.get(
                    "license_classifiers",
                    [],
                ),
            )

            environment_matches[
                environment_name
            ] = {
                **package,
                "review_flags": flags,
            }

        matches.append(
            {
                **requirement,
                "environment_matches": (
                    environment_matches
                ),
            }
        )

    return matches


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as source_file:
        while True:
            chunk = source_file.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(
                chunk
            )

    return digest.hexdigest()


def licence_file_evidence(
    path: Path,
) -> dict[str, Any]:
    source = path.read_text(
        encoding="utf-8-sig",
        errors="replace",
    )

    non_empty_lines = [
        line.strip()
        for line in source.splitlines()
        if line.strip()
    ]

    return {
        "path": str(
            path
        ),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(
            path
        ),
        "first_non_empty_lines": (
            non_empty_lines[:12]
        ),
    }


def find_licence_files(
    root: Path,
    *,
    maximum_depth: int = 5,
) -> list[dict[str, Any]]:
    if not root.exists():
        return []

    filename_patterns = [
        re.compile(
            r"^licen[cs]e(?:[._-].*)?$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^copying(?:[._-].*)?$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^notice(?:[._-].*)?$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^third[_-]?party(?:[._-].*)?$",
            re.IGNORECASE,
        ),
    ]

    results: list[
        dict[str, Any]
    ] = []

    for path in root.rglob(
        "*"
    ):
        if not path.is_file():
            continue

        try:
            relative_path = path.relative_to(
                root
            )

        except ValueError:
            continue

        if len(
            relative_path.parts
        ) > maximum_depth:
            continue

        if not any(
            pattern.match(
                path.name
            )
            for pattern in filename_patterns
        ):
            continue

        results.append(
            licence_file_evidence(
                path
            )
        )

    return sorted(
        results,
        key=lambda item: item[
            "path"
        ].lower(),
    )


def git_repository_evidence(
    root: Path,
) -> dict[str, Any]:
    git_check = run_command(
        [
            "git",
            "-C",
            str(
                root
            ),
            "rev-parse",
            "--is-inside-work-tree",
        ],
        working_directory=PROJECT_ROOT,
    )

    if (
        not git_check[
            "success"
        ]
        or git_check[
            "stdout"
        ].strip().lower()
        != "true"
    ):
        return {
            "is_git_repository": False,
            "remote_origin": None,
            "commit": None,
        }

    remote = run_command(
        [
            "git",
            "-C",
            str(
                root
            ),
            "config",
            "--get",
            "remote.origin.url",
        ],
        working_directory=PROJECT_ROOT,
    )

    commit = run_command(
        [
            "git",
            "-C",
            str(
                root
            ),
            "rev-parse",
            "HEAD",
        ],
        working_directory=PROJECT_ROOT,
    )

    return {
        "is_git_repository": True,
        "remote_origin": (
            remote[
                "stdout"
            ]
            if remote[
                "success"
            ]
            else None
        ),
        "commit": (
            commit[
                "stdout"
            ]
            if commit[
                "success"
            ]
            else None
        ),
    }


def read_node_package_metadata(
    package_name: str,
) -> dict[str, Any]:
    package_path = (
        NODE_MODULES_ROOT
        / package_name
        / "package.json"
    )

    if not package_path.exists():
        return {
            "name": package_name,
            "installed": False,
            "package_json": str(
                package_path
            ),
            "version": None,
            "license": None,
            "repository": None,
            "homepage": None,
            "review_flags": [
                "package-not-installed"
            ],
        }

    package_data = json.loads(
        package_path.read_text(
            encoding="utf-8-sig",
            errors="replace",
        )
    )

    licence_value = package_data.get(
        "license"
    )

    if isinstance(
        licence_value,
        dict,
    ):
        licence_text = json.dumps(
            licence_value,
            ensure_ascii=False,
        )

    elif isinstance(
        licence_value,
        list,
    ):
        licence_text = ", ".join(
            str(
                item
            )
            for item in licence_value
        )

    else:
        licence_text = str(
            licence_value
            or ""
        )

    repository_value = package_data.get(
        "repository"
    )

    if isinstance(
        repository_value,
        dict,
    ):
        repository_text = (
            repository_value.get(
                "url"
            )
            or json.dumps(
                repository_value,
                ensure_ascii=False,
            )
        )

    else:
        repository_text = (
            repository_value
            or ""
        )

    return {
        "name": package_data.get(
            "name"
        )
        or package_name,
        "installed": True,
        "package_json": str(
            package_path
        ),
        "version": package_data.get(
            "version"
        ),
        "license": licence_text,
        "repository": repository_text,
        "homepage": package_data.get(
            "homepage"
        ),
        "review_flags": classify_licence_record(
            licence_text,
            [],
        ),
    }


def frontend_inventory() -> dict[str, Any]:
    package_data = json.loads(
        PACKAGE_JSON_PATH.read_text(
            encoding="utf-8-sig"
        )
    )

    dependencies = package_data.get(
        "dependencies",
        {},
    )

    development_dependencies = package_data.get(
        "devDependencies",
        {},
    )

    combined_names = sorted(
        set(
            dependencies
        )
        | set(
            development_dependencies
        )
    )

    installed_metadata = [
        read_node_package_metadata(
            package_name
        )
        for package_name in combined_names
    ]

    return {
        "package_name": package_data.get(
            "name"
        ),
        "package_version": package_data.get(
            "version"
        ),
        "dependencies": dependencies,
        "dev_dependencies": (
            development_dependencies
        ),
        "direct_dependency_count": len(
            combined_names
        ),
        "installed_metadata": installed_metadata,
    }


print("=" * 92)
print(
    "MILESTONE 12.2A — THIRD-PARTY LICENCE "
    "TECHNICAL INVENTORY"
)
print("=" * 92)

for name, path in {
    "Project root": PROJECT_ROOT,
    "Backend root": BACKEND_ROOT,
    "Frontend root": FRONTEND_ROOT,
    "Backend requirements": REQUIREMENTS_PATH,
    "Frontend package manifest": PACKAGE_JSON_PATH,
    "CosyVoice source directory": COSYVOICE_ROOT,
    "IndicF5 source directory": INDICF5_ROOT,
    "Main backend Python": ROOT_PYTHON,
    "IndicF5 Python": INDIC_PYTHON,
    "CosyVoice Python": COSY_PYTHON,
}.items():
    check(
        name,
        path.exists(),
        str(
            path
        ),
    )


requirements = read_requirements(
    REQUIREMENTS_PATH
)

check(
    "Backend requirements were inventoried",
    requirements[
        "raw_entry_count"
    ]
    > 0,
)


print()
print(
    "Inspecting main backend environment..."
)

root_environment = (
    inventory_python_environment(
        "main-backend",
        ROOT_PYTHON,
    )
)

check(
    "Main backend package metadata was collected",
    root_environment[
        "package_count"
    ]
    > 0,
)


print(
    "Inspecting IndicF5 environment..."
)

indic_environment = (
    inventory_python_environment(
        "indicf5",
        INDIC_PYTHON,
    )
)

check(
    "IndicF5 package metadata was collected",
    indic_environment[
        "package_count"
    ]
    > 0,
)


print(
    "Inspecting CosyVoice environment..."
)

cosy_environment = (
    inventory_python_environment(
        "cosyvoice",
        COSY_PYTHON,
    )
)

check(
    "CosyVoice package metadata was collected",
    cosy_environment[
        "package_count"
    ]
    > 0,
)


environments = [
    root_environment,
    indic_environment,
    cosy_environment,
]


direct_requirement_matches = (
    match_direct_requirements(
        requirements,
        environments,
    )
)

check(
    "Direct Python requirements were matched",
    len(
        direct_requirement_matches
    )
    == len(
        requirements[
            "named_requirements"
        ]
    ),
)


frontend = frontend_inventory()

check(
    "Frontend direct dependencies were inventoried",
    frontend[
        "direct_dependency_count"
    ]
    > 0,
)


cosyvoice_licence_files = (
    find_licence_files(
        COSYVOICE_ROOT
    )
)

indicf5_licence_files = (
    find_licence_files(
        INDICF5_ROOT
    )
)

check(
    "CosyVoice licence-file scan completed",
    isinstance(
        cosyvoice_licence_files,
        list,
    ),
)

check(
    "IndicF5 licence-file scan completed",
    isinstance(
        indicf5_licence_files,
        list,
    ),
)


repository_evidence = {
    "project": git_repository_evidence(
        PROJECT_ROOT
    ),
    "cosyvoice": git_repository_evidence(
        COSYVOICE_ROOT
    ),
    "indicf5": git_repository_evidence(
        INDICF5_ROOT
    ),
}


python_review_flags = []

for requirement in direct_requirement_matches:
    for environment_name, package in (
        requirement[
            "environment_matches"
        ].items()
    ):
        if package is None:
            continue

        for flag in package[
            "review_flags"
        ]:
            python_review_flags.append(
                {
                    "requirement": requirement[
                        "raw"
                    ],
                    "environment": environment_name,
                    "package": package[
                        "name"
                    ],
                    "version": package[
                        "version"
                    ],
                    "flag": flag,
                    "license": package[
                        "license"
                    ],
                    "classifiers": package[
                        "license_classifiers"
                    ],
                }
            )


frontend_review_flags = []

for package in frontend[
    "installed_metadata"
]:
    for flag in package[
        "review_flags"
    ]:
        frontend_review_flags.append(
            {
                "package": package[
                    "name"
                ],
                "version": package[
                    "version"
                ],
                "flag": flag,
                "license": package[
                    "license"
                ],
            }
        )


report: dict[str, Any] = {
    "milestone": "12.2A",
    "created_at": datetime.now().isoformat(),
    "mode": (
        "read-only technical licence inventory"
    ),
    "legal_conclusion_made": False,
    "application_files_modified": False,
    "services_started": False,
    "checks_passed": checks_passed,
    "paths": {
        "project_root": str(
            PROJECT_ROOT
        ),
        "requirements": str(
            REQUIREMENTS_PATH
        ),
        "frontend_package_json": str(
            PACKAGE_JSON_PATH
        ),
        "cosyvoice_root": str(
            COSYVOICE_ROOT
        ),
        "indicf5_root": str(
            INDICF5_ROOT
        ),
    },
    "requirements": requirements,
    "python_environments": environments,
    "direct_requirement_matches": (
        direct_requirement_matches
    ),
    "frontend": frontend,
    "source_licence_files": {
        "cosyvoice": (
            cosyvoice_licence_files
        ),
        "indicf5": (
            indicf5_licence_files
        ),
    },
    "repository_evidence": (
        repository_evidence
    ),
    "review_flags": {
        "python": python_review_flags,
        "frontend": frontend_review_flags,
    },
}

JSON_REPORT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

JSON_REPORT_PATH.write_text(
    json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)


text_lines = [
    "=" * 92,
    (
        "MILESTONE 12.2A — THIRD-PARTY "
        "LICENCE TECHNICAL INVENTORY"
    ),
    "=" * 92,
    "",
    "PYTHON ENVIRONMENTS",
    "-" * 92,
]

for environment in environments:
    text_lines.append(
        f"{environment['environment_name']:20}: "
        f"{environment['package_count']} packages"
    )

text_lines.extend(
    [
        "",
        "DIRECT DEPENDENCIES",
        "-" * 92,
        (
            "Backend requirement entries : "
            f"{requirements['raw_entry_count']}"
        ),
        (
            "Named backend requirements  : "
            f"{len(requirements['named_requirements'])}"
        ),
        (
            "Frontend direct dependencies: "
            f"{frontend['direct_dependency_count']}"
        ),
        "",
        "SOURCE LICENCE FILES",
        "-" * 92,
        (
            "CosyVoice licence files      : "
            f"{len(cosyvoice_licence_files)}"
        ),
        (
            "IndicF5 licence files        : "
            f"{len(indicf5_licence_files)}"
        ),
        "",
        "MANUAL REVIEW FLAGS",
        "-" * 92,
        (
            "Python direct-dependency flags : "
            f"{len(python_review_flags)}"
        ),
        (
            "Frontend dependency flags      : "
            f"{len(frontend_review_flags)}"
        ),
    ]
)


if cosyvoice_licence_files:
    text_lines.extend(
        [
            "",
            "COSYVOICE LICENCE EVIDENCE",
            "-" * 92,
        ]
    )

    for evidence in cosyvoice_licence_files:
        text_lines.append(
            evidence[
                "path"
            ]
        )

        for line in evidence[
            "first_non_empty_lines"
        ][:5]:
            text_lines.append(
                f"  {line}"
            )


if indicf5_licence_files:
    text_lines.extend(
        [
            "",
            "INDICF5 LICENCE EVIDENCE",
            "-" * 92,
        ]
    )

    for evidence in indicf5_licence_files:
        text_lines.append(
            evidence[
                "path"
            ]
        )

        for line in evidence[
            "first_non_empty_lines"
        ][:5]:
            text_lines.append(
                f"  {line}"
            )


if python_review_flags:
    text_lines.extend(
        [
            "",
            "PYTHON ITEMS REQUIRING REVIEW",
            "-" * 92,
        ]
    )

    for item in python_review_flags[:40]:
        text_lines.append(
            f"{item['package']} "
            f"{item['version']} "
            f"[{item['environment']}] "
            f"-> {item['flag']} "
            f"({item['license'] or 'no licence field'})"
        )


if frontend_review_flags:
    text_lines.extend(
        [
            "",
            "FRONTEND ITEMS REQUIRING REVIEW",
            "-" * 92,
        ]
    )

    for item in frontend_review_flags[:40]:
        text_lines.append(
            f"{item['package']} "
            f"{item['version']} "
            f"-> {item['flag']} "
            f"({item['license'] or 'no licence field'})"
        )


text_lines.extend(
    [
        "",
        "IMPORTANT",
        "-" * 92,
        (
            "This report is a technical inventory. "
            "It does not make a legal compatibility decision."
        ),
        (
            "Repository licences, model-weight terms and "
            "dataset terms will be verified separately."
        ),
        "",
        "=" * 92,
        (
            "MILESTONE 12.2A THIRD-PARTY LICENCE "
            "TECHNICAL INVENTORY: COMPLETE"
        ),
        "=" * 92,
        f"Checks passed: {checks_passed}",
        "Application files modified: NO",
        "Services started: NO",
        "Legal conclusion made: NO",
        "",
        f"JSON report: {JSON_REPORT_PATH}",
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


check(
    "JSON licence inventory report was saved",
    (
        JSON_REPORT_PATH.exists()
        and JSON_REPORT_PATH.stat().st_size
        > 0
    ),
)

check(
    "Text licence inventory report was saved",
    (
        TEXT_REPORT_PATH.exists()
        and TEXT_REPORT_PATH.stat().st_size
        > 0
    ),
)


print()
print(
    "\n".join(
        text_lines
    )
)

print()
print(
    "Final checks passed:",
    checks_passed,
)
