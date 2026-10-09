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


def is_number(
    node: ast.AST | None,
    expected: float,
) -> bool:
    return (
        isinstance(
            node,
            ast.Constant,
        )
        and not isinstance(
            node.value,
            bool,
        )
        and isinstance(
            node.value,
            (
                int,
                float,
            ),
        )
        and float(
            node.value
        )
        == expected
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
            and node.name
            == "TTSService"
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
        for attribute
        in required_attributes
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


def locate_roles(
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
            "Expected exactly one requested-control "
            "validation call, found "
            f"{len(requested_validation)}."
        )

    if len(
        effective_validation
    ) != 1:
        raise RuntimeError(
            "Expected exactly one effective-control "
            "validation call, found "
            f"{len(effective_validation)}."
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
            "Expected exactly one routing_result "
            "assignment, found "
            f"{len(routing_assignments)}."
        )

    routing_assignment = (
        routing_assignments[0]
    )

    routing_calls = [
        node
        for node in ast.walk(
            routing_assignment.value
        )
        if isinstance(
            node,
            ast.Call,
        )
    ]

    speed_keyword_names = (
        "speed",
        "synthesis_speed",
        "requested_speed",
    )

    synthesis_candidates: list[
        tuple[
            ast.Call,
            str,
            ast.AST,
        ]
    ] = []

    for call in routing_calls:
        keywords = keyword_map(
            call
        )

        for speed_keyword in speed_keyword_names:
            speed_value = keywords.get(
                speed_keyword
            )

            if speed_value is not None:
                synthesis_candidates.append(
                    (
                        call,
                        speed_keyword,
                        speed_value,
                    )
                )

    if len(
        synthesis_candidates
    ) != 1:
        candidate_summary = [
            {
                "function": call_name(
                    call
                ),
                "line": call.lineno,
                "keyword": keyword_name,
            }
            for (
                call,
                keyword_name,
                _value,
            )
            in synthesis_candidates
        ]

        raise RuntimeError(
            "Expected exactly one synthesis-speed "
            "argument inside routing_result, found "
            f"{len(synthesis_candidates)}. "
            f"Candidates={candidate_summary}"
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
            "Expected exactly one final "
            "apply_audio_controls call, found "
            f"{len(final_calls)}."
        )

    synthesis_call, synthesis_keyword, synthesis_value = (
        synthesis_candidates[0]
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
        "synthesis_call": synthesis_call,
        "synthesis_keyword": synthesis_keyword,
        "synthesis_value": synthesis_value,
        "final_call": final_calls[0],
    }


source = TTS_PATH.read_text(
    encoding="utf-8-sig"
)

roles = locate_roles(
    source
)

requested_validation = roles[
    "requested_validation"
]

effective_validation = roles[
    "effective_validation"
]

synthesis_call = roles[
    "synthesis_call"
]

synthesis_keyword = roles[
    "synthesis_keyword"
]

synthesis_value = roles[
    "synthesis_value"
]

final_call = roles[
    "final_call"
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
        "Requested-control validation no longer "
        "uses the requested speed."
    )

required_final_names = {
    "volume": "effective_volume",
    "bass": "effective_bass",
    "speed": "effective_speed",
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
            "Final audio processing does not use "
            f"{expected_name} for {keyword_name}."
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


# Restore the effective validation that the false-positive
# patch incorrectly changed to speed=1.0.
effective_speed_value = (
    effective_keywords.get(
        "speed"
    )
)

if not is_name(
    effective_speed_value,
    "effective_speed",
):
    effective_start, effective_end = (
        source_offsets(
            source_bytes,
            effective_speed_value,
        )
    )

    replacements.append(
        (
            effective_start,
            effective_end,
            b"effective_speed",
        )
    )


# Only the call producing routing_result must use native speed.
if not is_number(
    synthesis_value,
    1.0,
):
    synthesis_start, synthesis_end = (
        source_offsets(
            source_bytes,
            synthesis_value,
        )
    )

    replacements.append(
        (
            synthesis_start,
            synthesis_end,
            b"1.0",
        )
    )


# Final joined output must always receive the resolved speed.
apply_speed_value = (
    final_keywords.get(
        "apply_speed"
    )
)

if apply_speed_value is None:
    raise RuntimeError(
        "Final audio processing has no "
        "apply_speed argument."
    )

if not (
    isinstance(
        apply_speed_value,
        ast.Constant,
    )
    and apply_speed_value.value
    is True
):
    apply_start, apply_end = (
        source_offsets(
            source_bytes,
            apply_speed_value,
        )
    )

    replacements.append(
        (
            apply_start,
            apply_end,
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

updated_roles = locate_roles(
    updated_source
)

updated_requested_keywords = keyword_map(
    updated_roles[
        "requested_validation"
    ]
)

updated_effective_keywords = keyword_map(
    updated_roles[
        "effective_validation"
    ]
)

updated_final_keywords = keyword_map(
    updated_roles[
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

if not is_number(
    updated_roles[
        "synthesis_value"
    ],
    1.0,
):
    raise RuntimeError(
        "Post-patch routing synthesis does not "
        "use native speed 1.0."
    )

if not is_name(
    updated_final_keywords.get(
        "speed"
    ),
    "effective_speed",
):
    raise RuntimeError(
        "Post-patch final processing lost "
        "effective_speed."
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

TTS_PATH.write_text(
    updated_source,
    encoding="utf-8",
)

print(
    "Requested validation line:",
    updated_roles[
        "requested_validation"
    ].lineno,
)

print(
    "Effective validation line:",
    updated_roles[
        "effective_validation"
    ].lineno,
)

print(
    "Routing synthesis call:",
    call_name(
        updated_roles[
            "synthesis_call"
        ]
    ),
)

print(
    "Routing synthesis line:",
    updated_roles[
        "synthesis_call"
    ].lineno,
)

print(
    "Routing speed keyword:",
    updated_roles[
        "synthesis_keyword"
    ],
)

print(
    "Final audio-control line:",
    updated_roles[
        "final_call"
    ].lineno,
)

print(
    "Milestone 10.7D-5A role-based "
    "correction: APPLIED"
)
