from __future__ import annotations

import ast
import json
from datetime import datetime
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

REPORT_PATH = (
    BACKEND_ROOT
    / "milestone_reports"
    / "milestone10_7d5e1_candidate_b_preflight.json"
)

CANDIDATE_B = {
    "style": "energetic",
    "speed_multiplier": 1.025,
    "volume_multiplier": 1.0,
    "bass_offset": 0.0,
    "presence_gain_db": 0.8,
    "presence_frequency_hz": 2800,
    "presence_q": 1.2,
    "compression": None,
}


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

        raise AssertionError(message)

    checks_passed += 1
    print(f"{name}: PASSED")


def call_name(
    call: ast.Call,
) -> str:
    if isinstance(call.func, ast.Attribute):
        return call.func.attr

    if isinstance(call.func, ast.Name):
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


def source_excerpt(
    source: str,
    start_line: int,
    end_line: int,
) -> str:
    lines = source.splitlines()

    safe_start = max(
        1,
        start_line,
    )

    safe_end = min(
        len(lines),
        end_line,
    )

    return "\n".join(
        f"{line_number:5}: {lines[line_number - 1]}"
        for line_number in range(
            safe_start,
            safe_end + 1,
        )
    )


def find_function(
    tree: ast.Module,
    function_name: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in ast.walk(tree):
        if (
            isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
            and node.name == function_name
        ):
            return node

    return None


def assignments_named(
    tree: ast.Module,
    expected_names: set[str],
) -> list[ast.Assign | ast.AnnAssign]:
    matches = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            names = {
                target.id
                for target in node.targets
                if isinstance(target, ast.Name)
            }

            if names & expected_names:
                matches.append(node)

        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id in expected_names
        ):
            matches.append(node)

    return matches


print("=" * 92)
print(
    "MILESTONE 10.7D-5E-1 — CANDIDATE B "
    "PRODUCTION INTEGRATION PREFLIGHT"
)
print("=" * 92)

check(
    "Style profile module exists",
    STYLE_PATH.exists(),
    str(STYLE_PATH),
)

check(
    "TTS service module exists",
    TTS_PATH.exists(),
    str(TTS_PATH),
)

style_source = STYLE_PATH.read_text(
    encoding="utf-8-sig"
)

tts_source = TTS_PATH.read_text(
    encoding="utf-8-sig"
)

style_tree = ast.parse(
    style_source,
    filename=str(STYLE_PATH),
)

tts_tree = ast.parse(
    tts_source,
    filename=str(TTS_PATH),
)

style_classes = [
    {
        "name": node.name,
        "line": node.lineno,
        "end_line": node.end_lineno,
        "fields": [
            statement.target.id
            for statement in node.body
            if (
                isinstance(statement, ast.AnnAssign)
                and isinstance(
                    statement.target,
                    ast.Name,
                )
            )
        ],
    }
    for node in style_tree.body
    if isinstance(node, ast.ClassDef)
]

check(
    "Style module contains at least one class",
    bool(style_classes),
    repr(style_classes),
)

profile_assignments = assignments_named(
    style_tree,
    {
        "STYLE_PROFILES",
        "VOICE_STYLE_PROFILES",
        "PROFILES",
    },
)

check(
    "Style profile registry assignment exists",
    len(profile_assignments) == 1,
    repr(
        [
            {
                "line": node.lineno,
                "end_line": node.end_lineno,
            }
            for node in profile_assignments
        ]
    ),
)

profile_assignment = profile_assignments[0]

resolve_function = find_function(
    style_tree,
    "resolve_style_controls",
)

check(
    "resolve_style_controls exists",
    resolve_function is not None,
)

apply_function = find_function(
    tts_tree,
    "apply_audio_controls",
)

check(
    "apply_audio_controls exists",
    apply_function is not None,
)

generate_function = find_function(
    tts_tree,
    "generate_speech",
)

check(
    "generate_speech exists",
    generate_function is not None,
)

apply_arguments = [
    argument.arg
    for argument in (
        apply_function.args.args
        + apply_function.args.kwonlyargs
    )
]

check(
    "Current audio controls include speed",
    "speed" in apply_arguments,
    repr(apply_arguments),
)

check(
    "Current audio controls include volume",
    "volume" in apply_arguments,
    repr(apply_arguments),
)

check(
    "Current audio controls include bass",
    "bass" in apply_arguments,
    repr(apply_arguments),
)

check(
    "Current audio controls include apply_speed",
    "apply_speed" in apply_arguments,
    repr(apply_arguments),
)

final_control_calls = [
    node
    for node in ast.walk(generate_function)
    if (
        isinstance(node, ast.Call)
        and call_name(node) == "apply_audio_controls"
    )
]

check(
    "Exactly one final audio-control call exists",
    len(final_control_calls) == 1,
    repr(
        [
            node.lineno
            for node in final_control_calls
        ]
    ),
)

final_control_call = final_control_calls[0]

final_keywords = keyword_map(
    final_control_call
)

check(
    "Final call passes effective speed",
    (
        isinstance(
            final_keywords.get("speed"),
            ast.Name,
        )
        and final_keywords["speed"].id
        == "effective_speed"
    ),
    (
        ast.dump(
            final_keywords.get("speed")
        )
        if final_keywords.get("speed")
        is not None
        else "Missing"
    ),
)


check(
    "Final call passes effective volume",
    (
        isinstance(
            final_keywords.get("volume"),
            ast.Name,
        )
        and final_keywords["volume"].id
        == "effective_volume"
    ),
)

check(
    "Final call passes effective bass",
    (
        isinstance(
            final_keywords.get("bass"),
            ast.Name,
        )
        and final_keywords["bass"].id
        == "effective_bass"
    ),
)

check(
    "Final call forces speed processing",
    (
        isinstance(
            final_keywords.get("apply_speed"),
            ast.Constant,
        )
        and final_keywords["apply_speed"].value
        is True
    ),
)

style_excerpt = source_excerpt(
    style_source,
    max(
        1,
        profile_assignment.lineno - 25,
    ),
    min(
        len(style_source.splitlines()),
        profile_assignment.end_lineno + 40,
    ),
)

resolve_excerpt = source_excerpt(
    style_source,
    max(
        1,
        resolve_function.lineno - 10,
    ),
    min(
        len(style_source.splitlines()),
        resolve_function.end_lineno + 10,
    ),
)

apply_excerpt = source_excerpt(
    tts_source,
    max(
        1,
        apply_function.lineno - 5,
    ),
    min(
        len(tts_source.splitlines()),
        apply_function.end_lineno + 5,
    ),
)

final_call_excerpt = source_excerpt(
    tts_source,
    max(
        1,
        final_control_call.lineno - 15,
    ),
    min(
        len(tts_source.splitlines()),
        final_control_call.end_lineno + 10,
    ),
)

report: dict[str, Any] = {
    "milestone": "10.7D-5E-1",
    "created_at": datetime.now().isoformat(),
    "selected_candidate": "B",
    "candidate_b_contract": CANDIDATE_B,
    "style_profile_path": str(STYLE_PATH),
    "tts_service_path": str(TTS_PATH),
    "style_classes": style_classes,
    "profile_assignment": {
        "line": profile_assignment.lineno,
        "end_line": profile_assignment.end_lineno,
    },
    "resolve_style_controls": {
        "line": resolve_function.lineno,
        "end_line": resolve_function.end_lineno,
    },
    "apply_audio_controls": {
        "line": apply_function.lineno,
        "end_line": apply_function.end_lineno,
        "arguments": apply_arguments,
    },
    "final_audio_control_call": {
        "line": final_control_call.lineno,
        "end_line": final_control_call.end_lineno,
        "keywords": sorted(final_keywords),
    },
    "excerpts": {
        "style_profiles": style_excerpt,
        "resolve_style_controls": resolve_excerpt,
        "apply_audio_controls": apply_excerpt,
        "final_audio_control_call": final_call_excerpt,
    },
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

check(
    "Preflight report was saved",
    (
        REPORT_PATH.exists()
        and REPORT_PATH.stat().st_size
        > 0
    ),
    str(REPORT_PATH),
)

print()
print("=" * 92)
print("LOCKED CANDIDATE B CONTRACT")
print("=" * 92)
print(
    json.dumps(
        CANDIDATE_B,
        ensure_ascii=False,
        indent=2,
    )
)

print()
print("=" * 92)
print("STYLE PROFILE CLASSES")
print("=" * 92)
print(
    json.dumps(
        style_classes,
        ensure_ascii=False,
        indent=2,
    )
)

print()
print("=" * 92)
print("STYLE PROFILE REGISTRY AND ENERGETIC ENTRY")
print("=" * 92)
print(style_excerpt)

print()
print("=" * 92)
print("STYLE CONTROL RESOLUTION")
print("=" * 92)
print(resolve_excerpt)

print()
print("=" * 92)
print("CURRENT AUDIO PROCESSING")
print("=" * 92)
print(apply_excerpt)

print()
print("=" * 92)
print("FINAL GENERATION CALL")
print("=" * 92)
print(final_call_excerpt)

print()
print("=" * 92)
print(
    "MILESTONE 10.7D-5E-1 CANDIDATE B "
    "INTEGRATION PREFLIGHT: PASSED"
)
print("=" * 92)
print("Checks passed:", checks_passed)
print()
print("Report:", REPORT_PATH)
