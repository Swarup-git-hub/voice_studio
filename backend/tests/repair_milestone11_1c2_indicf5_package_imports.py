from __future__ import annotations

import ast
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]

SERVER_PATH = (
    BACKEND_ROOT
    / "ai_models"
    / "indicf5"
    / "server.py"
)

SERVER_DIRECTORY = SERVER_PATH.parent


def is_local_module(
    module_name: str,
) -> bool:
    first_component = module_name.split(
        ".",
        maxsplit=1,
    )[0]

    sibling_module = (
        SERVER_DIRECTORY
        / f"{first_component}.py"
    )

    sibling_package = (
        SERVER_DIRECTORY
        / first_component
        / "__init__.py"
    )

    return (
        sibling_module.exists()
        or sibling_package.exists()
    )


source = SERVER_PATH.read_text(
    encoding="utf-8-sig"
)

tree = ast.parse(
    source,
    filename=str(
        SERVER_PATH
    ),
)

absolute_local_imports: list[
    ast.ImportFrom
] = []

for node in ast.walk(
    tree
):
    if not isinstance(
        node,
        ast.ImportFrom,
    ):
        continue

    if node.level != 0:
        continue

    if not node.module:
        continue

    if is_local_module(
        node.module
    ):
        absolute_local_imports.append(
            node
        )


existing_relative_config = any(
    isinstance(
        node,
        ast.ImportFrom,
    )
    and node.level == 1
    and node.module == "config"
    for node in ast.walk(
        tree
    )
)

absolute_config_found = any(
    node.module == "config"
    for node in absolute_local_imports
)

if (
    not absolute_config_found
    and not existing_relative_config
):
    raise RuntimeError(
        "Neither an absolute nor relative config import "
        "was found in IndicF5 server.py."
    )


lines = source.splitlines(
    keepends=True
)

patched_modules: list[str] = []

for node in sorted(
    absolute_local_imports,
    key=lambda item: item.lineno,
    reverse=True,
):
    line_index = (
        node.lineno - 1
    )

    original_token = (
        f"from {node.module} import"
    )

    replacement_token = (
        f"from .{node.module} import"
    )

    original_line = lines[
        line_index
    ]

    if original_token not in original_line:
        raise RuntimeError(
            "Could not locate the expected import token "
            f"on line {node.lineno}: {original_token}"
        )

    lines[
        line_index
    ] = original_line.replace(
        original_token,
        replacement_token,
        1,
    )

    patched_modules.append(
        node.module
    )


updated_source = "".join(
    lines
)

updated_tree = ast.parse(
    updated_source,
    filename=str(
        SERVER_PATH
    ),
)

remaining_local_absolute_imports = []

for node in ast.walk(
    updated_tree
):
    if not isinstance(
        node,
        ast.ImportFrom,
    ):
        continue

    if (
        node.level == 0
        and node.module
        and is_local_module(
            node.module
        )
    ):
        remaining_local_absolute_imports.append(
            {
                "module": node.module,
                "line": node.lineno,
            }
        )


if remaining_local_absolute_imports:
    raise RuntimeError(
        "Package-local absolute imports remain: "
        f"{remaining_local_absolute_imports}"
    )


relative_config_found = any(
    isinstance(
        node,
        ast.ImportFrom,
    )
    and node.level == 1
    and node.module == "config"
    for node in ast.walk(
        updated_tree
    )
)

if not relative_config_found:
    raise RuntimeError(
        "The required relative config import was not created."
    )


if patched_modules:
    SERVER_PATH.write_text(
        updated_source,
        encoding="utf-8",
    )

    print(
        "Converted package-local imports:"
    )

    for module_name in sorted(
        set(
            patched_modules
        )
    ):
        print(
            f"  from {module_name} import "
            f"-> from .{module_name} import"
        )

else:
    print(
        "IndicF5 package-local imports were already relative."
    )


print(
    "Milestone 11.1C-2 IndicF5 package imports: REPAIRED"
)
