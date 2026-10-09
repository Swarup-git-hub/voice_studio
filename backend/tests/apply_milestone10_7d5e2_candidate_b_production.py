from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]

STYLE_PATH = (
    BACKEND_ROOT
    / "app"
    / "audio"
    / "style_profiles.py"
)

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


def find_class(
    tree: ast.Module,
    expected_name: str,
) -> ast.ClassDef:
    for node in tree.body:
        if (
            isinstance(
                node,
                ast.ClassDef,
            )
            and node.name == expected_name
        ):
            return node

    raise RuntimeError(
        f"Class {expected_name} was not found."
    )


def find_function(
    tree: ast.Module,
    expected_name: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef:
    for node in ast.walk(
        tree
    ):
        if (
            isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
            and node.name == expected_name
        ):
            return node

    raise RuntimeError(
        f"Function {expected_name} was not found."
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
        for attribute in required_attributes
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


def replace_node(
    source: str,
    node: ast.AST,
    replacement: str,
) -> str:
    source_bytes = source.encode(
        "utf-8"
    )

    start, end = source_offsets(
        source_bytes,
        node,
    )

    updated_bytes = (
        source_bytes[:start]
        + replacement.encode(
            "utf-8"
        )
        + source_bytes[end:]
    )

    return updated_bytes.decode(
        "utf-8"
    )


def find_profile_dictionary(
    tree: ast.Module,
) -> ast.Dict:
    for node in tree.body:
        value: ast.AST | None = None

        if isinstance(
            node,
            ast.Assign,
        ):
            target_names = {
                target.id
                for target in node.targets
                if isinstance(
                    target,
                    ast.Name,
                )
            }

            if "_STYLE_PROFILES" in target_names:
                value = node.value

        elif (
            isinstance(
                node,
                ast.AnnAssign,
            )
            and isinstance(
                node.target,
                ast.Name,
            )
            and node.target.id
            == "_STYLE_PROFILES"
        ):
            value = node.value

        if isinstance(
            value,
            ast.Dict,
        ):
            return value

    raise RuntimeError(
        "_STYLE_PROFILES dictionary was not found."
    )


def find_profile_call(
    tree: ast.Module,
    profile_name: str,
) -> ast.Call:
    profile_dictionary = find_profile_dictionary(
        tree
    )

    for key, value in zip(
        profile_dictionary.keys,
        profile_dictionary.values,
    ):
        if (
            isinstance(
                key,
                ast.Constant,
            )
            and key.value == profile_name
            and isinstance(
                value,
                ast.Call,
            )
        ):
            return value

    raise RuntimeError(
        f"Style profile {profile_name} was not found."
    )


# ============================================================
# Patch style_profiles.py in memory
# ============================================================

style_source = STYLE_PATH.read_text(
    encoding="utf-8-sig"
)

style_tree = ast.parse(
    style_source,
    filename=str(
        STYLE_PATH
    ),
)

style_profile_class = find_class(
    style_tree,
    "StyleProfile",
)

style_field_names = {
    statement.target.id
    for statement in style_profile_class.body
    if (
        isinstance(
            statement,
            ast.AnnAssign,
        )
        and isinstance(
            statement.target,
            ast.Name,
        )
    )
}

new_presence_fields = {
    "presence_gain_db",
    "presence_frequency_hz",
    "presence_q",
}

existing_presence_fields = (
    style_field_names
    & new_presence_fields
)

if not existing_presence_fields:
    field_pattern = re.compile(
        r"(?m)^(?P<indent>[ \t]+)"
        r"bass_offset_db:\s*float\s*$"
    )

    style_source, field_count = (
        field_pattern.subn(
            lambda match: (
                match.group(0)
                + "\n"
                + match.group("indent")
                + "presence_gain_db: float = 0.0\n"
                + match.group("indent")
                + "presence_frequency_hz: int = 2800\n"
                + match.group("indent")
                + "presence_q: float = 1.2"
            ),
            style_source,
            count=1,
        )
    )

    if field_count != 1:
        raise RuntimeError(
            "Could not add presence fields to StyleProfile."
        )

elif existing_presence_fields != new_presence_fields:
    raise RuntimeError(
        "StyleProfile contains a partial presence-field "
        f"integration: {sorted(existing_presence_fields)}"
    )


style_tree = ast.parse(
    style_source,
    filename=str(
        STYLE_PATH
    ),
)

energetic_call = find_profile_call(
    style_tree,
    "energetic",
)

candidate_b_call = '''StyleProfile(
        name="energetic",
        description=(
            "Slightly quicker delivery with a mild "
            "clarity and vocal-presence lift."
        ),
        speed_multiplier=1.025,
        volume_multiplier=1.0,
        bass_offset_db=0.0,
        presence_gain_db=0.8,
        presence_frequency_hz=2800,
        presence_q=1.2,
    )'''

style_source = replace_node(
    style_source,
    energetic_call,
    candidate_b_call,
)


# ============================================================
# Patch tts_service.py in memory
# ============================================================

tts_source = TTS_PATH.read_text(
    encoding="utf-8-sig"
)

tts_tree = ast.parse(
    tts_source,
    filename=str(
        TTS_PATH
    ),
)

apply_function = find_function(
    tts_tree,
    "apply_audio_controls",
)

apply_argument_names = {
    argument.arg
    for argument in (
        apply_function.args.args
        + apply_function.args.kwonlyargs
    )
}

presence_arguments = {
    "presence_gain_db",
    "presence_frequency_hz",
    "presence_q",
}

existing_presence_arguments = (
    apply_argument_names
    & presence_arguments
)

if not existing_presence_arguments:
    signature_pattern = re.compile(
        r"(?m)^(?P<indent>[ \t]+)"
        r"apply_speed:\s*bool\s*=\s*False,\s*$"
    )

    tts_source, signature_count = (
        signature_pattern.subn(
            lambda match: (
                match.group(0)
                + "\n"
                + match.group("indent")
                + "presence_gain_db: float = 0.0,\n"
                + match.group("indent")
                + "presence_frequency_hz: int = 2800,\n"
                + match.group("indent")
                + "presence_q: float = 1.2,"
            ),
            tts_source,
            count=1,
        )
    )

    if signature_count != 1:
        raise RuntimeError(
            "Could not add presence arguments to "
            "apply_audio_controls."
        )

elif existing_presence_arguments != presence_arguments:
    raise RuntimeError(
        "apply_audio_controls contains a partial "
        "presence integration: "
        f"{sorted(existing_presence_arguments)}"
    )


presence_filter_marker = (
    "        # Candidate B style-presence processing."
)

if presence_filter_marker not in tts_source:
    bass_comment = (
        "        # Bass is measured in decibels."
    )

    presence_filter = '''        # Candidate B style-presence processing.
        if abs(presence_gain_db) >= 0.01:
            if not 100 <= presence_frequency_hz <= 10000:
                raise ValueError(
                    "Presence frequency must be between "
                    "100 and 10000 Hz."
                )

            if not 0.1 <= presence_q <= 10.0:
                raise ValueError(
                    "Presence Q must be between 0.1 and 10.0."
                )

            if not -6.0 <= presence_gain_db <= 6.0:
                raise ValueError(
                    "Presence gain must be between "
                    "-6.0 and 6.0 dB."
                )

            filters.append(
                "equalizer="
                f"f={presence_frequency_hz}:"
                "t=q:"
                f"w={presence_q:.2f}:"
                f"g={presence_gain_db:.2f}"
            )

'''

    if tts_source.count(
        bass_comment
    ) != 1:
        raise RuntimeError(
            "Expected exactly one bass-processing marker."
        )

    tts_source = tts_source.replace(
        bass_comment,
        presence_filter
        + bass_comment,
        1,
    )


tts_tree = ast.parse(
    tts_source,
    filename=str(
        TTS_PATH
    ),
)

apply_function = find_function(
    tts_tree,
    "apply_audio_controls",
)

limiter_statements: list[
    ast.Expr
] = []

for node in ast.walk(
    apply_function
):
    if not isinstance(
        node,
        ast.Expr,
    ):
        continue

    if not isinstance(
        node.value,
        ast.Call,
    ):
        continue

    call = node.value

    if call_name(
        call
    ) != "append":
        continue

    if not call.args:
        continue

    first_argument = call.args[0]

    if (
        isinstance(
            first_argument,
            ast.Constant,
        )
        and isinstance(
            first_argument.value,
            str,
        )
        and first_argument.value.startswith(
            "alimiter="
        )
    ):
        limiter_statements.append(
            node
        )

if len(
    limiter_statements
) != 1:
    raise RuntimeError(
        "Expected exactly one limiter append statement, "
        f"found {len(limiter_statements)}."
    )

limiter_statement = limiter_statements[0]

limiter_replacement = '''if (
            volume > 1.001
            or bass > 0.01
            or presence_gain_db > 1.5
        ):
            filters.append(
                "alimiter="
                "limit=0.95:"
                "level=false:"
                "latency=1"
            )'''

tts_source = replace_node(
    tts_source,
    limiter_statement,
    limiter_replacement,
)


tts_tree = ast.parse(
    tts_source,
    filename=str(
        TTS_PATH
    ),
)

generate_function = find_function(
    tts_tree,
    "generate_speech",
)

final_calls = [
    node
    for node in ast.walk(
        generate_function
    )
    if (
        isinstance(
            node,
            ast.Call,
        )
        and call_name(
            node
        )
        == "apply_audio_controls"
    )
]

if len(
    final_calls
) != 1:
    raise RuntimeError(
        "Expected exactly one final apply_audio_controls "
        f"call, found {len(final_calls)}."
    )

final_call = final_calls[0]

final_keywords = keyword_map(
    final_call
)

missing_presence_keywords = (
    presence_arguments
    - set(
        final_keywords
    )
)

if missing_presence_keywords:
    if set(
        final_keywords
    ) & presence_arguments:
        raise RuntimeError(
            "Final audio-control call contains a partial "
            "presence integration."
        )

    lines = tts_source.splitlines(
        keepends=True
    )

    closing_line_index = (
        final_call.end_lineno - 1
    )

    closing_line = lines[
        closing_line_index
    ]

    closing_indent_match = re.match(
        r"[ \t]*",
        closing_line,
    )

    if closing_indent_match is None:
        raise RuntimeError(
            "Could not determine final call indentation."
        )

    closing_indent = (
        closing_indent_match.group(0)
    )

    keyword_indent = (
        closing_indent
        + "    "
    )

    presence_keyword_source = (
        keyword_indent
        + "presence_gain_db="
        + "style_controls.profile.presence_gain_db,\n"
        + keyword_indent
        + "presence_frequency_hz="
        + "style_controls.profile.presence_frequency_hz,\n"
        + keyword_indent
        + "presence_q="
        + "style_controls.profile.presence_q,\n"
    )

    lines.insert(
        closing_line_index,
        presence_keyword_source,
    )

    tts_source = "".join(
        lines
    )


# ============================================================
# Guarded post-patch verification
# ============================================================

updated_style_tree = ast.parse(
    style_source,
    filename=str(
        STYLE_PATH
    ),
)

updated_style_class = find_class(
    updated_style_tree,
    "StyleProfile",
)

updated_style_fields = {
    statement.target.id
    for statement in updated_style_class.body
    if (
        isinstance(
            statement,
            ast.AnnAssign,
        )
        and isinstance(
            statement.target,
            ast.Name,
        )
    )
}

if not presence_arguments.issubset(
    updated_style_fields
):
    raise RuntimeError(
        "StyleProfile presence fields are incomplete."
    )

updated_energetic_call = find_profile_call(
    updated_style_tree,
    "energetic",
)

updated_energetic_keywords = keyword_map(
    updated_energetic_call
)

expected_energetic_values: dict[
    str,
    Any,
] = {
    "speed_multiplier": 1.025,
    "volume_multiplier": 1.0,
    "bass_offset_db": 0.0,
    "presence_gain_db": 0.8,
    "presence_frequency_hz": 2800,
    "presence_q": 1.2,
}

for keyword_name, expected_value in (
    expected_energetic_values.items()
):
    keyword_node = updated_energetic_keywords.get(
        keyword_name
    )

    if keyword_node is None:
        raise RuntimeError(
            "Energetic profile is missing "
            f"{keyword_name}."
        )

    actual_value = ast.literal_eval(
        keyword_node
    )

    if actual_value != expected_value:
        raise RuntimeError(
            "Energetic profile has an invalid "
            f"{keyword_name}: {actual_value}"
        )


updated_tts_tree = ast.parse(
    tts_source,
    filename=str(
        TTS_PATH
    ),
)

updated_apply_function = find_function(
    updated_tts_tree,
    "apply_audio_controls",
)

updated_apply_arguments = {
    argument.arg
    for argument in (
        updated_apply_function.args.args
        + updated_apply_function.args.kwonlyargs
    )
}

if not presence_arguments.issubset(
    updated_apply_arguments
):
    raise RuntimeError(
        "apply_audio_controls presence arguments "
        "are incomplete."
    )

updated_generate_function = find_function(
    updated_tts_tree,
    "generate_speech",
)

updated_final_calls = [
    node
    for node in ast.walk(
        updated_generate_function
    )
    if (
        isinstance(
            node,
            ast.Call,
        )
        and call_name(
            node
        )
        == "apply_audio_controls"
    )
]

if len(
    updated_final_calls
) != 1:
    raise RuntimeError(
        "Post-patch final audio-control call count "
        "is invalid."
    )

updated_final_keywords = keyword_map(
    updated_final_calls[0]
)

if not presence_arguments.issubset(
    updated_final_keywords
):
    raise RuntimeError(
        "Final audio-control call does not pass all "
        "presence settings."
    )

required_tts_markers = [
    "Candidate B style-presence processing.",
    "equalizer=",
    "presence_gain_db > 1.5",
]

for marker in required_tts_markers:
    if marker not in tts_source:
        raise RuntimeError(
            "TTS service is missing marker: "
            f"{marker}"
        )


STYLE_PATH.write_text(
    style_source,
    encoding="utf-8",
)

TTS_PATH.write_text(
    tts_source,
    encoding="utf-8",
)

print(
    "Milestone 10.7D-5E-2 Candidate B "
    "production integration: APPLIED"
)
