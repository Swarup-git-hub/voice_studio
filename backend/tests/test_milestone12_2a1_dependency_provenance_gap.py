from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(
    os.environ[
        "MILESTONE12_2A1_PROJECT_ROOT"
    ]
).resolve()

BACKEND_ROOT = PROJECT_ROOT / "backend"

REQUIREMENTS_PATH = (
    BACKEND_ROOT
    / "requirements.txt"
)

APP_ROOT = (
    BACKEND_ROOT
    / "app"
)

INDICF5_ROOT = (
    BACKEND_ROOT
    / "ai_models"
    / "indicf5"
)

COSYVOICE_ROOT = (
    BACKEND_ROOT
    / "ai_models"
    / "cosyvoice"
)

ROOT_PYTHON = Path(
    os.environ[
        "MILESTONE12_2A1_ROOT_PYTHON"
    ]
).resolve()

INDIC_PYTHON = Path(
    os.environ[
        "MILESTONE12_2A1_INDIC_PYTHON"
    ]
).resolve()

COSY_PYTHON = Path(
    os.environ[
        "MILESTONE12_2A1_COSY_PYTHON"
    ]
).resolve()

JSON_REPORT_PATH = Path(
    os.environ[
        "MILESTONE12_2A1_JSON_REPORT"
    ]
).resolve()

TEXT_REPORT_PATH = Path(
    os.environ[
        "MILESTONE12_2A1_TEXT_REPORT"
    ]
).resolve()


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


def normalise_distribution_name(
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
    timeout_seconds: int = 180,
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=str(
                BACKEND_ROOT
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
        "success": (
            completed.returncode == 0
        ),
        "return_code": (
            completed.returncode
        ),
        "stdout": (
            completed.stdout.strip()
        ),
        "stderr": (
            completed.stderr.strip()
        ),
    }


try:
    from packaging.requirements import (
        Requirement,
    )

except ImportError:
    Requirement = None


def classify_requirement(
    line: str,
) -> dict[str, Any]:
    include_match = re.match(
        r"^(?:-r|--requirement)\s+(.+)$",
        line,
        flags=re.IGNORECASE,
    )

    if include_match:
        return {
            "category": "included-file",
            "name": None,
            "target": (
                include_match.group(
                    1
                ).strip()
            ),
        }

    editable_match = re.match(
        r"^(?:-e|--editable)\s+(.+)$",
        line,
        flags=re.IGNORECASE,
    )

    if editable_match:
        target = editable_match.group(
            1
        ).strip()

        egg_match = re.search(
            r"(?:#|&)egg=([^&]+)",
            target,
            flags=re.IGNORECASE,
        )

        return {
            "category": "editable",
            "name": (
                egg_match.group(
                    1
                )
                if egg_match
                else None
            ),
            "target": target,
        }

    if line.startswith(
        "-"
    ):
        return {
            "category": "installer-option",
            "name": None,
            "target": line,
        }

    if Requirement is not None:
        try:
            parsed = Requirement(
                line
            )

            return {
                "category": (
                    "direct-reference"
                    if parsed.url
                    else "named-requirement"
                ),
                "name": parsed.name,
                "target": parsed.url,
                "specifier": str(
                    parsed.specifier
                ),
                "marker": (
                    str(
                        parsed.marker
                    )
                    if parsed.marker
                    else None
                ),
            }

        except Exception:
            pass

    fallback_match = re.match(
        r"^([A-Za-z0-9_.-]+)"
        r"(?:\s*@\s*(.+)|.*)$",
        line,
    )

    if fallback_match:
        return {
            "category": (
                "direct-reference"
                if fallback_match.group(
                    2
                )
                else "named-requirement"
            ),
            "name": fallback_match.group(
                1
            ),
            "target": fallback_match.group(
                2
            ),
        }

    return {
        "category": "unresolved",
        "name": None,
        "target": line,
    }


def parse_requirement_file(
    path: Path,
    *,
    visited: set[Path] | None = None,
) -> list[dict[str, Any]]:
    resolved_path = path.resolve()

    if visited is None:
        visited = set()

    if resolved_path in visited:
        return [
            {
                "source_file": str(
                    resolved_path
                ),
                "line_number": None,
                "raw": "",
                "category": (
                    "included-file-cycle"
                ),
                "name": None,
                "target": None,
            }
        ]

    visited.add(
        resolved_path
    )

    records: list[
        dict[str, Any]
    ] = []

    for line_number, raw_line in enumerate(
        path.read_text(
            encoding="utf-8-sig",
            errors="replace",
        ).splitlines(),
        start=1,
    ):
        stripped = raw_line.strip()

        if (
            not stripped
            or stripped.startswith("#")
        ):
            continue

        classification = classify_requirement(
            stripped
        )

        record = {
            "source_file": str(
                resolved_path
            ),
            "line_number": line_number,
            "raw": stripped,
            **classification,
        }

        records.append(
            record
        )

        if (
            classification[
                "category"
            ]
            == "included-file"
        ):
            target = classification.get(
                "target"
            )

            if not target:
                continue

            include_path = Path(
                target
            )

            if not include_path.is_absolute():
                include_path = (
                    path.parent
                    / include_path
                )

            record[
                "resolved_include"
            ] = str(
                include_path.resolve()
            )

            record[
                "include_exists"
            ] = include_path.exists()

            if include_path.exists():
                records.extend(
                    parse_requirement_file(
                        include_path,
                        visited=visited,
                    )
                )

    return records


def scan_imports(
    paths: list[Path],
) -> dict[str, list[dict[str, Any]]]:
    imports: dict[
        str,
        list[dict[str, Any]]
    ] = {}

    source_files: list[Path] = []

    for path in paths:
        if path.is_file():
            source_files.append(
                path
            )

        elif path.is_dir():
            source_files.extend(
                sorted(
                    path.rglob(
                        "*.py"
                    )
                )
            )

    for source_path in source_files:
        if "__pycache__" in source_path.parts:
            continue

        try:
            source = source_path.read_text(
                encoding="utf-8-sig",
                errors="replace",
            )

            tree = ast.parse(
                source,
                filename=str(
                    source_path
                ),
            )

        except (
            OSError,
            SyntaxError,
        ):
            continue

        for node in ast.walk(
            tree
        ):
            module_names: list[str] = []

            if isinstance(
                node,
                ast.Import,
            ):
                module_names = [
                    alias.name
                    for alias in node.names
                ]

            elif (
                isinstance(
                    node,
                    ast.ImportFrom,
                )
                and node.level == 0
                and node.module
            ):
                module_names = [
                    node.module
                ]

            for module_name in module_names:
                top_level = module_name.split(
                    ".",
                    maxsplit=1,
                )[0]

                imports.setdefault(
                    top_level,
                    [],
                ).append(
                    {
                        "file": str(
                            source_path.relative_to(
                                BACKEND_ROOT
                            )
                        ),
                        "line": node.lineno,
                        "import": module_name,
                    }
                )

    return dict(
        sorted(
            imports.items()
        )
    )


ENVIRONMENT_HELPER = r'''
from __future__ import annotations

import importlib.metadata as metadata
import json
import sys


package_to_distributions = (
    metadata.packages_distributions()
)

distributions = {}


for distribution in metadata.distributions():
    package_metadata = distribution.metadata

    name = (
        package_metadata.get(
            "Name"
        )
        or distribution.name
        or "UNKNOWN"
    )

    licence_value = (
        package_metadata.get(
            "License"
        )
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

    distributions[
        name
    ] = {
        "name": name,
        "version": (
            distribution.version
            or ""
        ),
        "license": licence_value,
        "license_classifiers": (
            licence_classifiers
        ),
        "home_page": (
            package_metadata.get(
                "Home-page"
            )
            or ""
        ),
    }


print(
    json.dumps(
        {
            "executable": sys.executable,
            "python_version": sys.version,
            "package_to_distributions": (
                package_to_distributions
            ),
            "distributions": distributions,
        },
        ensure_ascii=False,
    )
)
'''


def environment_inventory(
    environment_name: str,
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
            ENVIRONMENT_HELPER,
        ]
    )

    if not result[
        "success"
    ]:
        raise RuntimeError(
            f"Could not inspect {environment_name}.\n"
            f"{result['stderr']}"
        )

    payload = json.loads(
        result[
            "stdout"
        ]
    )

    payload[
        "environment_name"
    ] = environment_name

    return payload


def classify_licence(
    licence: str,
    classifiers: list[str],
) -> list[str]:
    combined = " ".join(
        [
            licence,
            *classifiers,
        ]
    ).strip().lower()

    flags: list[str] = []

    if not combined:
        flags.append(
            "missing-licence-metadata"
        )

    if combined in {
        "unknown",
        "none",
        "n/a",
    }:
        flags.append(
            "unclear-licence-metadata"
        )

    flag_markers = {
        "agpl": "agpl-review",
        "affero": "agpl-review",
        "lgpl": "lgpl-review",
        (
            "lesser general public"
        ): "lgpl-review",
        "gpl": "gpl-review",
        (
            "general public license"
        ): "gpl-review",
        "non-commercial": (
            "non-commercial-review"
        ),
        "noncommercial": (
            "non-commercial-review"
        ),
        "proprietary": (
            "proprietary-review"
        ),
        "custom": (
            "custom-licence-review"
        ),
        "licenseref": (
            "custom-licence-review"
        ),
    }

    for marker, flag in (
        flag_markers.items()
    ):
        if (
            marker in combined
            and flag not in flags
        ):
            flags.append(
                flag
            )

    return flags


def dependency_evidence(
    imports: dict[
        str,
        list[dict[str, Any]]
    ],
    environment: dict[str, Any],
) -> list[dict[str, Any]]:
    package_mapping = environment[
        "package_to_distributions"
    ]

    distributions = environment[
        "distributions"
    ]

    distribution_index = {
        normalise_distribution_name(
            name
        ): metadata
        for name, metadata in (
            distributions.items()
        )
    }

    local_modules = {
        "app",
        "ai_models",
        "config",
        "engine",
        "schemas",
        "server",
        "tests",
    }

    evidence: list[
        dict[str, Any]
    ] = []

    for module_name, occurrences in (
        imports.items()
    ):
        if (
            module_name
            in sys.stdlib_module_names
            or module_name
            in local_modules
        ):
            continue

        distribution_names = (
            package_mapping.get(
                module_name
            )
            or []
        )

        if not distribution_names:
            fallback = (
                distribution_index.get(
                    normalise_distribution_name(
                        module_name
                    )
                )
            )

            distribution_names = (
                [
                    fallback[
                        "name"
                    ]
                ]
                if fallback
                else []
            )

        matched_distributions = []

        for distribution_name in (
            distribution_names
        ):
            metadata = (
                distributions.get(
                    distribution_name
                )
                or distribution_index.get(
                    normalise_distribution_name(
                        distribution_name
                    )
                )
            )

            if metadata is None:
                continue

            matched_distributions.append(
                {
                    **metadata,
                    "review_flags": (
                        classify_licence(
                            metadata.get(
                                "license",
                                "",
                            ),
                            metadata.get(
                                "license_classifiers",
                                [],
                            ),
                        )
                    ),
                }
            )

        evidence.append(
            {
                "module": module_name,
                "occurrences": occurrences,
                "distributions": (
                    matched_distributions
                ),
                "unresolved": (
                    not matched_distributions
                ),
            }
        )

    return evidence


def provenance_markers(
    root: Path,
) -> list[dict[str, Any]]:
    markers: list[
        dict[str, Any]
    ] = []

    allowed_suffixes = {
        ".py",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".md",
        ".txt",
    }

    keywords = {
        "from_pretrained",
        "repo_id",
        "model_id",
        "model_name",
        "huggingface",
        "hf_hub",
        "ai4bharat",
        "indicf5",
        "cosyvoice",
        "modelscope",
    }

    url_pattern = re.compile(
        r"https?://[^\s\"'<>]+"
    )

    repository_id_pattern = re.compile(
        r"""["']([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)["']"""
    )

    for path in sorted(
        root.rglob(
            "*"
        )
    ):
        if (
            not path.is_file()
            or path.suffix.lower()
            not in allowed_suffixes
            or "__pycache__"
            in path.parts
        ):
            continue

        try:
            source = path.read_text(
                encoding="utf-8-sig",
                errors="replace",
            )

        except OSError:
            continue

        for line_number, line in enumerate(
            source.splitlines(),
            start=1,
        ):
            lowered = line.lower()

            if not any(
                keyword in lowered
                for keyword in keywords
            ):
                continue

            urls = url_pattern.findall(
                line
            )

            repository_ids = (
                repository_id_pattern.findall(
                    line
                )
            )

            markers.append(
                {
                    "file": str(
                        path.relative_to(
                            BACKEND_ROOT
                        )
                    ),
                    "line": line_number,
                    "text": line.strip()[
                        :500
                    ],
                    "urls": urls,
                    "repository_ids": (
                        repository_ids
                    ),
                }
            )

    return markers


print("=" * 92)
print(
    "MILESTONE 12.2A-1 — DEPENDENCY AND "
    "MODEL-PROVENANCE GAP RESOLUTION"
)
print("=" * 92)


for name, path in {
    "Backend requirements": (
        REQUIREMENTS_PATH
    ),
    "Application source": APP_ROOT,
    "IndicF5 source": INDICF5_ROOT,
    "CosyVoice source": COSYVOICE_ROOT,
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


requirement_records = (
    parse_requirement_file(
        REQUIREMENTS_PATH
    )
)

named_requirements = [
    record
    for record in requirement_records
    if record.get(
        "name"
    )
]

unresolved_requirements = [
    record
    for record in requirement_records
    if record[
        "category"
    ]
    in {
        "unresolved",
        "installer-option",
        "included-file-cycle",
    }
]


check(
    "Requirement entries were classified",
    len(
        requirement_records
    )
    > 0,
)


main_imports = scan_imports(
    [
        APP_ROOT,
    ]
)

indic_imports = scan_imports(
    [
        INDICF5_ROOT,
    ]
)

cosy_server_path = (
    COSYVOICE_ROOT
    / "server.py"
)

cosy_imports = scan_imports(
    [
        cosy_server_path,
    ]
)


check(
    "Main application imports were scanned",
    bool(
        main_imports
    ),
)

check(
    "IndicF5 imports were scanned",
    bool(
        indic_imports
    ),
)

check(
    "CosyVoice service imports were scanned",
    bool(
        cosy_imports
    ),
)


print()
print(
    "Inspecting main backend environment..."
)

main_environment = (
    environment_inventory(
        "main-backend",
        ROOT_PYTHON,
    )
)

print(
    "Inspecting IndicF5 environment..."
)

indic_environment = (
    environment_inventory(
        "indicf5",
        INDIC_PYTHON,
    )
)

print(
    "Inspecting CosyVoice environment..."
)

cosy_environment = (
    environment_inventory(
        "cosyvoice",
        COSY_PYTHON,
    )
)


main_dependencies = dependency_evidence(
    main_imports,
    main_environment,
)

indic_dependencies = dependency_evidence(
    indic_imports,
    indic_environment,
)

cosy_dependencies = dependency_evidence(
    cosy_imports,
    cosy_environment,
)


check(
    "Main imported dependencies were resolved",
    any(
        item[
            "distributions"
        ]
        for item in main_dependencies
    ),
)

check(
    "IndicF5 imported dependencies were resolved",
    any(
        item[
            "distributions"
        ]
        for item in indic_dependencies
    ),
)

check(
    "CosyVoice service dependencies were resolved",
    any(
        item[
            "distributions"
        ]
        for item in cosy_dependencies
    ),
)


indic_provenance = provenance_markers(
    INDICF5_ROOT
)

cosy_provenance = provenance_markers(
    COSYVOICE_ROOT
)


check(
    "IndicF5 provenance scan completed",
    isinstance(
        indic_provenance,
        list,
    ),
)

check(
    "CosyVoice provenance scan completed",
    isinstance(
        cosy_provenance,
        list,
    ),
)


all_dependency_groups = {
    "main-backend": main_dependencies,
    "indicf5": indic_dependencies,
    "cosyvoice-server": cosy_dependencies,
}


review_flags: list[
    dict[str, Any]
] = []

unresolved_modules: list[
    dict[str, Any]
] = []


for environment_name, dependencies in (
    all_dependency_groups.items()
):
    for dependency in dependencies:
        if dependency[
            "unresolved"
        ]:
            unresolved_modules.append(
                {
                    "environment": (
                        environment_name
                    ),
                    "module": dependency[
                        "module"
                    ],
                    "occurrences": (
                        dependency[
                            "occurrences"
                        ]
                    ),
                }
            )

        for distribution in (
            dependency[
                "distributions"
            ]
        ):
            for flag in distribution[
                "review_flags"
            ]:
                review_flags.append(
                    {
                        "environment": (
                            environment_name
                        ),
                        "module": dependency[
                            "module"
                        ],
                        "distribution": (
                            distribution[
                                "name"
                            ]
                        ),
                        "version": (
                            distribution[
                                "version"
                            ]
                        ),
                        "license": (
                            distribution[
                                "license"
                            ]
                        ),
                        "classifiers": (
                            distribution[
                                "license_classifiers"
                            ]
                        ),
                        "flag": flag,
                    }
                )


report: dict[str, Any] = {
    "milestone": "12.2A-1",
    "created_at": datetime.now().isoformat(),
    "mode": (
        "read-only dependency and provenance audit"
    ),
    "application_files_modified": False,
    "services_started": False,
    "legal_conclusion_made": False,
    "checks_passed_before_report": (
        checks_passed
    ),
    "requirements": {
        "path": str(
            REQUIREMENTS_PATH
        ),
        "record_count": len(
            requirement_records
        ),
        "named_count": len(
            named_requirements
        ),
        "unresolved_count": len(
            unresolved_requirements
        ),
        "records": requirement_records,
    },
    "dependency_evidence": (
        all_dependency_groups
    ),
    "unresolved_import_modules": (
        unresolved_modules
    ),
    "review_flags": review_flags,
    "provenance": {
        "indicf5": indic_provenance,
        "cosyvoice": cosy_provenance,
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
        "MILESTONE 12.2A-1 — DEPENDENCY AND "
        "MODEL-PROVENANCE GAP RESOLUTION"
    ),
    "=" * 92,
    "",
    "REQUIREMENTS CLASSIFICATION",
    "-" * 92,
    (
        "Total classified records : "
        f"{len(requirement_records)}"
    ),
    (
        "Named requirements       : "
        f"{len(named_requirements)}"
    ),
    (
        "Unresolved/options       : "
        f"{len(unresolved_requirements)}"
    ),
    "",
]


for record in requirement_records:
    text_lines.append(
        (
            f"{Path(record['source_file']).name}:"
            f"{record['line_number']} "
            f"[{record['category']}] "
            f"name={record.get('name')!r} "
            f"raw={record['raw']!r}"
        )
    )


text_lines.extend(
    [
        "",
        "APPLICATION IMPORT DEPENDENCY EVIDENCE",
        "-" * 92,
    ]
)


for environment_name, dependencies in (
    all_dependency_groups.items()
):
    resolved_count = sum(
        1
        for item in dependencies
        if item[
            "distributions"
        ]
    )

    unresolved_count = sum(
        1
        for item in dependencies
        if item[
            "unresolved"
        ]
    )

    text_lines.append(
        (
            f"{environment_name:20}: "
            f"{resolved_count} resolved, "
            f"{unresolved_count} unresolved"
        )
    )


for environment_name, dependencies in (
    all_dependency_groups.items()
):
    text_lines.extend(
        [
            "",
            environment_name.upper(),
        ]
    )

    for dependency in dependencies:
        if dependency[
            "distributions"
        ]:
            distribution_text = ", ".join(
                (
                    f"{item['name']} "
                    f"{item['version']} "
                    f"[{item['license'] or 'no licence field'}]"
                )
                for item in dependency[
                    "distributions"
                ]
            )

        else:
            distribution_text = (
                "UNRESOLVED"
            )

        text_lines.append(
            (
                f"  {dependency['module']} "
                f"-> {distribution_text}"
            )
        )


text_lines.extend(
    [
        "",
        "INDICF5 PROVENANCE MARKERS",
        "-" * 92,
    ]
)


if indic_provenance:
    for item in indic_provenance[:80]:
        text_lines.append(
            (
                f"{item['file']}:{item['line']} "
                f"{item['text']}"
            )
        )

else:
    text_lines.append(
        "No explicit IndicF5 provenance markers found."
    )


text_lines.extend(
    [
        "",
        "COSYVOICE PROVENANCE MARKERS",
        "-" * 92,
    ]
)


if cosy_provenance:
    for item in cosy_provenance[:80]:
        text_lines.append(
            (
                f"{item['file']}:{item['line']} "
                f"{item['text']}"
            )
        )

else:
    text_lines.append(
        "No explicit CosyVoice provenance markers found."
    )


text_lines.extend(
    [
        "",
        "LICENCE REVIEW FLAGS",
        "-" * 92,
        (
            "Flagged imported distributions: "
            f"{len(review_flags)}"
        ),
        (
            "Unresolved imported modules     : "
            f"{len(unresolved_modules)}"
        ),
    ]
)


for item in review_flags[:100]:
    text_lines.append(
        (
            f"{item['environment']} | "
            f"{item['distribution']} "
            f"{item['version']} | "
            f"{item['flag']} | "
            f"{item['license'] or 'no licence field'}"
        )
    )


for item in unresolved_modules[:100]:
    text_lines.append(
        (
            f"UNRESOLVED | "
            f"{item['environment']} | "
            f"{item['module']}"
        )
    )


text_lines.extend(
    [
        "",
        "IMPORTANT",
        "-" * 92,
        (
            "This remains a technical evidence report. "
            "It does not make a legal conclusion."
        ),
        "",
        "=" * 92,
        (
            "MILESTONE 12.2A-1 DEPENDENCY AND "
            "PROVENANCE GAP RESOLUTION: COMPLETE"
        ),
        "=" * 92,
        (
            f"Checks passed before reports: "
            f"{checks_passed}"
        ),
        "Application files modified: NO",
        "Services started: NO",
        "Licence selected: NO",
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
    "JSON gap-resolution report was saved",
    (
        JSON_REPORT_PATH.exists()
        and JSON_REPORT_PATH.stat().st_size
        > 0
    ),
)

check(
    "Text gap-resolution report was saved",
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
