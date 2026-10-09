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


def function_name(
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


def node_offsets(
    source_bytes: bytes,
    node: ast.AST,
) -> tuple[int, int]:
    if (
        not hasattr(node, "lineno")
        or not hasattr(node, "end_lineno")
        or not hasattr(node, "col_offset")
        or not hasattr(node, "end_col_offset")
    ):
        raise RuntimeError(
            "AST node does not contain source offsets."
        )

    lines = source_bytes.splitlines(
        keepends=True
    )

    line_starts: list[int] = []
    current_offset = 0

    for line in lines:
        line_starts.append(
            current_offset
        )

        current_offset += len(
            line
        )

    start = (
        line_starts[
            node.lineno - 1
        ]
        + node.col_offset
    )

    end = (
        line_starts[
            node.end_lineno - 1
        ]
        + node.end_col_offset
    )

    return start, end


def is_name(
    node: ast.AST | None,
    expected_name: str,
) -> bool:
    return (
        isinstance(
            node,
            ast.Name,
        )
        and node.id == expected_name
    )


source_bytes = TTS_PATH.read_bytes()

source = source_bytes.decode(
    "utf-8-sig"
)

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

final_control_calls = [
    call
    for call in calls
    if function_name(
        call
    )
    == "apply_audio_controls"
]

if len(final_control_calls) != 1:
    raise RuntimeError(
        "Expected exactly one final "
        "apply_audio_controls call, found "
        f"{len(final_control_calls)}."
    )

final_control_call = (
    final_control_calls[0]
)

final_keywords = keyword_map(
    final_control_call
)

required_final_keywords = {
    "raw_audio",
    "final_audio",
    "volume",
    "bass",
    "speed",
    "apply_speed",
}

missing_final_keywords = (
    required_final_keywords
    - set(
        final_keywords
    )
)

if missing_final_keywords:
    raise RuntimeError(
        "Final audio-control call is missing: "
        f"{sorted(missing_final_keywords)}"
    )

if not is_name(
    final_keywords["speed"],
    "effective_speed",
):
    raise RuntimeError(
        "Final audio processing does not use "
        "effective_speed."
    )

if not is_name(
    final_keywords["volume"],
    "effective_volume",
):
    raise RuntimeError(
        "Final audio processing does not use "
        "effective_volume."
    )

if not is_name(
    final_keywords["bass"],
    "effective_bass",
):
    raise RuntimeError(
        "Final audio processing does not use "
        "effective_bass."
    )


# Find the neural/coordinator call that currently receives
# effective_speed. Exclude final audio processing itself.
neural_speed_candidates: list[
    tuple[
        ast.Call,
        ast.AST,
    ]
] = []

for call in calls:
    if call is final_control_call:
        continue

    keywords = keyword_map(
        call
    )

    speed_value = keywords.get(
        "speed"
    )

    if is_name(
        speed_value,
        "effective_speed",
    ):
        neural_speed_candidates.append(
            (
                call,
                speed_value,
            )
        )

if len(neural_speed_candidates) != 1:
    candidate_summary = [
        {
            "function": function_name(
                call
            ),
            "line": call.lineno,
        }
        for call, _value
        in neural_speed_candidates
    ]

    raise RuntimeError(
        "Expected exactly one neural synthesis "
        "call receiving effective_speed, found "
        f"{len(neural_speed_candidates)}. "
        f"Candidates={candidate_summary}"
    )

neural_call, neural_speed_value = (
    neural_speed_candidates[0]
)

replacements: list[
    tuple[
        int,
        int,
        bytes,
    ]
] = []

neural_start, neural_end = (
    node_offsets(
        source.encode(
            "utf-8"
        ),
        neural_speed_value,
    )
)

replacements.append(
    (
        neural_start,
        neural_end,
        b"1.0",
    )
)

apply_speed_value = (
    final_keywords[
        "apply_speed"
    ]
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
        node_offsets(
            source.encode(
                "utf-8"
            ),
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


updated_bytes = source.encode(
    "utf-8"
)

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

updated_tree = ast.parse(
    updated_source,
    filename=str(
        TTS_PATH
    ),
)

updated_generate = find_generate_method(
    updated_tree
)

updated_calls = [
    node
    for node in ast.walk(
        updated_generate
    )
    if isinstance(
        node,
        ast.Call,
    )
]

updated_final_calls = [
    call
    for call in updated_calls
    if function_name(
        call
    )
    == "apply_audio_controls"
]

if len(updated_final_calls) != 1:
    raise RuntimeError(
        "Post-patch final audio-control "
        "call count is invalid."
    )

updated_final_call = (
    updated_final_calls[0]
)

updated_final_keywords = keyword_map(
    updated_final_call
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

remaining_neural_effective_speed = []

native_speed_calls = []

for call in updated_calls:
    if call is updated_final_call:
        continue

    keywords = keyword_map(
        call
    )

    speed_value = keywords.get(
        "speed"
    )

    if is_name(
        speed_value,
        "effective_speed",
    ):
        remaining_neural_effective_speed.append(
            function_name(
                call
            )
        )

    if (
        isinstance(
            speed_value,
            ast.Constant,
        )
        and float(
            speed_value.value
        )
        == 1.0
    ):
        native_speed_calls.append(
            {
                "function": function_name(
                    call
                ),
                "line": call.lineno,
            }
        )

if remaining_neural_effective_speed:
    raise RuntimeError(
        "effective_speed still reaches neural "
        "synthesis: "
        f"{remaining_neural_effective_speed}"
    )

if not native_speed_calls:
    raise RuntimeError(
        "No native-speed neural synthesis call "
        "was found after the patch."
    )

TTS_PATH.write_text(
    updated_source,
    encoding="utf-8",
)

print(
    "Neural synthesis call:",
    function_name(
        neural_call
    ),
)

print(
    "Neural synthesis line:",
    neural_call.lineno,
)

print(
    "Final audio-control line:",
    final_control_call.lineno,
)

print(
    "Milestone 10.7D-5A AST-based "
    "deterministic correction: APPLIED"
)
