from __future__ import annotations

import ast
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]

PACKAGE_ROOT = (
    BACKEND_ROOT
    / "ai_models"
    / "indicf5"
)

BACKUP_ROOT = Path(
    os.environ[
        "MILESTONE_BACKUP_ROOT"
    ]
).resolve()

REPORT_PATH = Path(
    os.environ[
        "MILESTONE_REPORT_PATH"
    ]
).resolve()


def module_exists(
    directory: Path,
    first_component: str,
) -> bool:
    return (
        (
            directory
            / f"{first_component}.py"
        ).is_file()
        or (
            directory
            / first_component
            / "__init__.py"
        ).is_file()
    )


def relative_import_prefix(
    *,
    source_path: Path,
    module_name: str,
) -> str | None:
    first_component = module_name.split(
        ".",
        maxsplit=1,
    )[0]

    source_directory = source_path.parent

    # Prefer a module or package beside the importing file.
    if module_exists(
        source_directory,
        first_component,
    ):
        target_file = (
            source_directory
            / f"{first_component}.py"
        )

        if target_file.resolve() != source_path.resolve():
            return "."

        target_package = (
            source_directory
            / first_component
            / "__init__.py"
        )

        if target_package.exists():
            return "."

    # Otherwise, check for a module at the IndicF5 package root.
    if module_exists(
        PACKAGE_ROOT,
        first_component,
    ):
        relative_parent = source_directory.relative_to(
            PACKAGE_ROOT
        )

        levels_up = (
            len(
                relative_parent.parts
            )
            + 1
        )

        return "." * levels_up

    return None


def source_offsets(
    source_bytes: bytes,
    node: ast.AST,
) -> tuple[int, int]:
    required_attributes = (
        "lineno",
        "col_offset",
        "end_lineno",
        "end_col_offset",
    )

    if not all(
        hasattr(
            node,
            attribute,
        )
        for attribute in required_attributes
    ):
        raise RuntimeError(
            "AST source offsets are unavailable."
        )

    lines = source_bytes.splitlines(
        keepends=True
    )

    line_offsets: list[int] = []

    running_offset = 0

    for line in lines:
        line_offsets.append(
            running_offset
        )

        running_offset += len(
            line
        )

    start = (
        line_offsets[
            node.lineno - 1
        ]
        + node.col_offset
    )

    end = (
        line_offsets[
            node.end_lineno - 1
        ]
        + node.end_col_offset
    )

    return start, end


def find_absolute_local_imports(
    *,
    source_path: Path,
    source: str,
) -> tuple[
    list[
        tuple[
            ast.ImportFrom,
            str,
        ]
    ],
    list[
        dict[str, Any]
    ],
]:
    tree = ast.parse(
        source,
        filename=str(
            source_path
        ),
    )

    import_from_matches: list[
        tuple[
            ast.ImportFrom,
            str,
        ]
    ] = []

    unsupported_imports: list[
        dict[str, Any]
    ] = []

    for node in ast.walk(
        tree
    ):
        if isinstance(
            node,
            ast.ImportFrom,
        ):
            if (
                node.level != 0
                or not node.module
            ):
                continue

            prefix = relative_import_prefix(
                source_path=source_path,
                module_name=node.module,
            )

            if prefix is not None:
                import_from_matches.append(
                    (
                        node,
                        prefix,
                    )
                )

            continue

        if isinstance(
            node,
            ast.Import,
        ):
            local_aliases = []

            for alias in node.names:
                prefix = relative_import_prefix(
                    source_path=source_path,
                    module_name=alias.name,
                )

                if prefix is not None:
                    local_aliases.append(
                        alias.name
                    )

            if local_aliases:
                unsupported_imports.append(
                    {
                        "file": str(
                            source_path
                        ),
                        "line": node.lineno,
                        "modules": local_aliases,
                    }
                )

    return (
        import_from_matches,
        unsupported_imports,
    )


python_files = sorted(
    path
    for path in PACKAGE_ROOT.rglob(
        "*.py"
    )
    if "__pycache__"
    not in path.parts
)

if not python_files:
    raise RuntimeError(
        f"No Python files were found under {PACKAGE_ROOT}."
    )


all_unsupported_imports: list[
    dict[str, Any]
] = []

planned_updates: dict[
    Path,
    tuple[
        str,
        list[
            dict[str, Any]
        ],
    ]
] = {}


for source_path in python_files:
    source = source_path.read_text(
        encoding="utf-8-sig"
    )

    matches, unsupported = find_absolute_local_imports(
        source_path=source_path,
        source=source,
    )

    all_unsupported_imports.extend(
        unsupported
    )

    if not matches:
        continue

    source_bytes = source.encode(
        "utf-8"
    )

    replacements: list[
        tuple[
            int,
            int,
            bytes,
            dict[str, Any],
        ]
    ] = []

    for node, prefix in matches:
        if not node.module:
            continue

        start, end = source_offsets(
            source_bytes,
            node,
        )

        original_segment = source_bytes[
            start:end
        ].decode(
            "utf-8"
        )

        pattern = re.compile(
            r"^from\s+"
            + re.escape(
                node.module
            )
            + r"\s+import\b"
        )

        replacement_header = (
            f"from {prefix}{node.module} import"
        )

        updated_segment, replacement_count = (
            pattern.subn(
                replacement_header,
                original_segment,
                count=1,
            )
        )

        if replacement_count != 1:
            raise RuntimeError(
                "Could not rewrite package-local import.\n"
                f"File: {source_path}\n"
                f"Line: {node.lineno}\n"
                f"Segment: {original_segment}"
            )

        replacement_detail = {
            "file": str(
                source_path.relative_to(
                    PACKAGE_ROOT
                )
            ),
            "line": node.lineno,
            "before": (
                f"from {node.module} import"
            ),
            "after": replacement_header,
        }

        replacements.append(
            (
                start,
                end,
                updated_segment.encode(
                    "utf-8"
                ),
                replacement_detail,
            )
        )

    updated_bytes = source_bytes

    replacement_details: list[
        dict[str, Any]
    ] = []

    for (
        start,
        end,
        replacement_bytes,
        replacement_detail,
    ) in sorted(
        replacements,
        key=lambda item: item[0],
        reverse=True,
    ):
        updated_bytes = (
            updated_bytes[:start]
            + replacement_bytes
            + updated_bytes[end:]
        )

        replacement_details.append(
            replacement_detail
        )

    updated_source = updated_bytes.decode(
        "utf-8"
    )

    ast.parse(
        updated_source,
        filename=str(
            source_path
        ),
    )

    planned_updates[
        source_path
    ] = (
        updated_source,
        list(
            reversed(
                replacement_details
            )
        ),
    )


if all_unsupported_imports:
    raise RuntimeError(
        "Package-local 'import module' statements require "
        "manual review before modification:\n"
        + json.dumps(
            all_unsupported_imports,
            ensure_ascii=False,
            indent=2,
        )
    )


patched_imports: list[
    dict[str, Any]
] = []


for source_path, (
    updated_source,
    replacement_details,
) in planned_updates.items():
    relative_path = source_path.relative_to(
        PACKAGE_ROOT
    )

    backup_path = (
        BACKUP_ROOT
        / "indicf5"
        / relative_path
    )

    backup_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        source_path,
        backup_path,
    )

    source_path.write_text(
        updated_source,
        encoding="utf-8",
    )

    patched_imports.extend(
        replacement_details
    )


remaining_imports: list[
    dict[str, Any]
] = []

remaining_unsupported: list[
    dict[str, Any]
] = []


for source_path in python_files:
    source = source_path.read_text(
        encoding="utf-8-sig"
    )

    matches, unsupported = find_absolute_local_imports(
        source_path=source_path,
        source=source,
    )

    remaining_unsupported.extend(
        unsupported
    )

    for node, prefix in matches:
        remaining_imports.append(
            {
                "file": str(
                    source_path.relative_to(
                        PACKAGE_ROOT
                    )
                ),
                "line": node.lineno,
                "module": node.module,
                "required_prefix": prefix,
            }
        )


if remaining_imports:
    raise RuntimeError(
        "Package-local absolute from-imports remain:\n"
        + json.dumps(
            remaining_imports,
            ensure_ascii=False,
            indent=2,
        )
    )


if remaining_unsupported:
    raise RuntimeError(
        "Package-local absolute imports remain:\n"
        + json.dumps(
            remaining_unsupported,
            ensure_ascii=False,
            indent=2,
        )
    )


report = {
    "milestone": "11.1C-2",
    "repair": "IndicF5 package-local imports",
    "created_at": datetime.now().isoformat(),
    "package_root": str(
        PACKAGE_ROOT
    ),
    "backup_root": str(
        BACKUP_ROOT
    ),
    "python_files_scanned": len(
        python_files
    ),
    "files_modified": len(
        planned_updates
    ),
    "imports_modified": len(
        patched_imports
    ),
    "patched_imports": patched_imports,
    "remaining_absolute_local_imports": [],
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
    "IndicF5 Python files scanned:",
    len(
        python_files
    ),
)

print(
    "IndicF5 files modified:",
    len(
        planned_updates
    ),
)

print(
    "Package-local imports converted:",
    len(
        patched_imports
    ),
)


if patched_imports:
    for item in patched_imports:
        print(
            " ",
            item[
                "file"
            ],
            "line",
            item[
                "line"
            ],
            ":",
            item[
                "before"
            ],
            "->",
            item[
                "after"
            ],
        )

else:
    print(
        "All IndicF5 package-local imports were already relative."
    )


print(
    "Package-local absolute imports remaining: 0"
)

print(
    "Repair report:",
    REPORT_PATH,
)

print(
    "Milestone 11.1C-2 complete IndicF5 "
    "package import repair: PASSED"
)
