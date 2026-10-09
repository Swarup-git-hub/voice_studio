from __future__ import annotations

import ast
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]

TTS_PATH = (
    BACKEND_ROOT
    / "app"
    / "services"
    / "tts_service.py"
)


def call_name(
    call: ast.Call,
) -> str:
    if isinstance(
        call.func,
        ast.Attribute,
    ):
        return call.func.attr

    if isinstance(
        call.func,
        ast.Name,
    ):
        return call.func.id

    return ""


def keyword_map(
    call: ast.Call,
) -> dict[str, ast.AST]:
    return {
        keyword.arg: keyword.value
        for keyword in call.keywords
        if keyword.arg is not None
    }


def is_name(
    node: ast.AST | None,
    expected: str,
) -> bool:
    return (
        isinstance(
            node,
            ast.Name,
        )
        and node.id == expected
    )


def targets_name(
    assignment: ast.Assign,
    expected: str,
) -> bool:
    return any(
        isinstance(
            target,
            ast.Name,
        )
        and target.id == expected
        for target in assignment.targets
    )


def find_generate_method(
    tree: ast.Module,
) -> ast.FunctionDef | ast.AsyncFunctionDef:
    for node in tree.body:
        if not (
            isinstance(
                node,
                ast.ClassDef,
            )
            and node.name == "TTSService"
        ):
            continue

        for statement in node.body:
            if (
                isinstance(
                    statement,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                    ),
                )
                and statement.name
                == "generate_speech"
            ):
                return statement

    raise RuntimeError(
        "TTSService.generate_speech was not found."
    )


def source_offsets(
    source_bytes: bytes,
    node: ast.AST,
) -> tuple[int, int]:
    required = (
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
        for attribute in required
    ):
        raise RuntimeError(
            "AST source offsets are unavailable."
        )

    lines = source_bytes.splitlines(
        keepends=True
    )

    line_offsets: list[int] = []

    current_offset = 0

    for line in lines:
        line_offsets.append(
            current_offset
        )

        current_offset += len(
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


def locate_contract(
    source: str,
) -> dict[str, object]:
    tree = ast.parse(
        source,
        filename=str(
            TTS_PATH
        ),
    )

    generate_method = find_generate_method(
        tree
    )

    calls = [
        node
        for node in ast.walk(
            generate_method
        )
        if isinstance(
            node,
            ast.Call,
        )
    ]

    validation_calls = [
        call
        for call in calls
        if call_name(
            call
        )
        == "validate_controls"
    ]

    requested_validation = []

    effective_validation = []

    for call in validation_calls:
        keywords = keyword_map(
            call
        )

        if (
            is_name(
                keywords.get(
                    "volume"
                ),
                "volume",
            )
            and is_name(
                keywords.get(
                    "bass"
                ),
                "bass",
            )
        ):
            requested_validation.append(
                call
            )

        if (
            is_name(
                keywords.get(
                    "volume"
                ),
                "effective_volume",
            )
            and is_name(
                keywords.get(
                    "bass"
                ),
                "effective_bass",
            )
        ):
            effective_validation.append(
                call
            )

    if len(
        requested_validation
    ) != 1:
        raise RuntimeError(
            "Expected one requested-control validation, "
            f"found {len(requested_validation)}."
        )

    if len(
        effective_validation
    ) != 1:
        raise RuntimeError(
            "Expected one effective-control validation, "
            f"found {len(effective_validation)}."
        )

    final_calls = [
        call
        for call in calls
        if call_name(
            call
        )
        == "apply_audio_controls"
    ]

    if len(
        final_calls
    ) != 1:
        raise RuntimeError(
            "Expected one final audio-control call, "
            f"found {len(final_calls)}."
        )

    routing_assignments = [
        node
        for node in ast.walk(
            generate_method
        )
        if (
            isinstance(
                node,
                ast.Assign,
            )
            and targets_name(
                node,
                "routing_result",
            )
        )
    ]

    if len(
        routing_assignments
    ) != 1:
        raise RuntimeError(
            "Expected one routing_result assignment, "
            f"found {len(routing_assignments)}."
        )

    return {
        "tree": tree,
        "generate_method": generate_method,
        "requested_validation": (
            requested_validation[0]
        ),
        "effective_validation": (
            effective_validation[0]
        ),
        "final_call": final_calls[0],
        "routing_assignment": (
            routing_assignments[0]
        ),
    }


source = TTS_PATH.read_text(
    encoding="utf-8-sig"
)

contract = locate_contract(
    source
)

requested_validation = contract[
    "requested_validation"
]

effective_validation = contract[
    "effective_validation"
]

final_call = contract[
    "final_call"
]

routing_assignment = contract[
    "routing_assignment"
]

requested_keywords = keyword_map(
    requested_validation
)

effective_keywords = keyword_map(
    effective_validation
)

final_keywords = keyword_map(
    final_call
)

if not is_name(
    requested_keywords.get(
        "speed"
    ),
    "speed",
):
    raise RuntimeError(
        "Requested validation does not use "
        "the requested speed."
    )

effective_speed_node = (
    effective_keywords.get(
        "speed"
    )
)

if effective_speed_node is None:
    raise RuntimeError(
        "Effective validation has no speed argument."
    )

required_final_names = {
    "speed": "effective_speed",
    "volume": "effective_volume",
    "bass": "effective_bass",
}

for keyword_name, expected_name in (
    required_final_names.items()
):
    if not is_name(
        final_keywords.get(
            keyword_name
        ),
        expected_name,
    ):
        raise RuntimeError(
            "Final processing does not use "
            f"{expected_name} for {keyword_name}."
        )

apply_speed_node = final_keywords.get(
    "apply_speed"
)

if apply_speed_node is None:
    raise RuntimeError(
        "Final processing has no apply_speed argument."
    )

source_bytes = source.encode(
    "utf-8"
)

replacements: list[
    tuple[
        int,
        int,
        bytes,
    ]
] = []


# Restore the effective validation damaged by the
# earlier false-positive AST patch.
if not is_name(
    effective_speed_node,
    "effective_speed",
):
    start, end = source_offsets(
        source_bytes,
        effective_speed_node,
    )

    replacements.append(
        (
            start,
            end,
            b"effective_speed",
        )
    )


# Keep deterministic style timing in the final shared
# FFmpeg processing stage.
if not (
    isinstance(
        apply_speed_node,
        ast.Constant,
    )
    and apply_speed_node.value
    is True
):
    start, end = source_offsets(
        source_bytes,
        apply_speed_node,
    )

    replacements.append(
        (
            start,
            end,
            b"True",
        )
    )


updated_bytes = source_bytes

for start, end, replacement in sorted(
    replacements,
    key=lambda item: item[0],
    reverse=True,
):
    updated_bytes = (
        updated_bytes[:start]
        + replacement
        + updated_bytes[end:]
    )

updated_source = updated_bytes.decode(
    "utf-8"
)

updated_contract = locate_contract(
    updated_source
)

updated_requested_keywords = keyword_map(
    updated_contract[
        "requested_validation"
    ]
)

updated_effective_keywords = keyword_map(
    updated_contract[
        "effective_validation"
    ]
)

updated_final_keywords = keyword_map(
    updated_contract[
        "final_call"
    ]
)

if not is_name(
    updated_requested_keywords.get(
        "speed"
    ),
    "speed",
):
    raise RuntimeError(
        "Post-patch requested validation is invalid."
    )

if not is_name(
    updated_effective_keywords.get(
        "speed"
    ),
    "effective_speed",
):
    raise RuntimeError(
        "Post-patch effective validation is invalid."
    )

for keyword_name, expected_name in (
    required_final_names.items()
):
    if not is_name(
        updated_final_keywords.get(
            keyword_name
        ),
        expected_name,
    ):
        raise RuntimeError(
            "Post-patch final processing lost "
            f"{expected_name}."
        )

updated_apply_speed = (
    updated_final_keywords.get(
        "apply_speed"
    )
)

if not (
    isinstance(
        updated_apply_speed,
        ast.Constant,
    )
    and updated_apply_speed.value
    is True
):
    raise RuntimeError(
        "Post-patch final processing does not "
        "force apply_speed=True."
    )

routing_source = ast.unparse(
    updated_contract[
        "routing_assignment"
    ]
)

TTS_PATH.write_text(
    updated_source,
    encoding="utf-8",
)

print(
    "Requested validation line:",
    updated_contract[
        "requested_validation"
    ].lineno,
)

print(
    "Effective validation line:",
    updated_contract[
        "effective_validation"
    ].lineno,
)

print(
    "Final audio-control line:",
    updated_contract[
        "final_call"
    ].lineno,
)

print()
print("Routing assignment:")
print(routing_source)

print()
print(
    "Milestone 10.7D-5A final-stage "
    "correction: APPLIED"
)
