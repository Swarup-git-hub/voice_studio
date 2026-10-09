from __future__ import annotations

import ast
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
FRONTEND_ROOT = PROJECT_ROOT / "frontend"

REPORT_FOLDER = (
    BACKEND_ROOT
    / "milestone_reports"
)

CONTRACT_PATH = (
    REPORT_FOLDER
    / "voice_style_contract_v1.json"
)

AUDIT_PATH = (
    REPORT_FOLDER
    / "milestone10_7a_style_audit.json"
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

        raise AssertionError(message)

    checks_passed += 1
    print(f"{name}: PASSED")


def read_source(
    path: Path,
) -> str:
    return path.read_text(
        encoding="utf-8-sig",
    )


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as source_file:
        while True:
            block = source_file.read(
                1024 * 1024
            )

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


def class_field_names(
    path: Path,
    class_name: str,
) -> list[str]:
    tree = ast.parse(
        read_source(path),
        filename=str(path),
    )

    for node in tree.body:
        if (
            isinstance(node, ast.ClassDef)
            and node.name == class_name
        ):
            fields: list[str] = []

            for statement in node.body:
                if isinstance(
                    statement,
                    ast.AnnAssign,
                ):
                    if isinstance(
                        statement.target,
                        ast.Name,
                    ):
                        fields.append(
                            statement.target.id
                        )

                elif isinstance(
                    statement,
                    ast.Assign,
                ):
                    for target in statement.targets:
                        if isinstance(
                            target,
                            ast.Name,
                        ):
                            fields.append(
                                target.id
                            )

            return sorted(
                set(fields)
            )

    raise RuntimeError(
        f"Class {class_name!r} was not found "
        f"in {path}."
    )


def method_parameter_names(
    path: Path,
    class_name: str,
    method_name: str,
) -> list[str]:
    tree = ast.parse(
        read_source(path),
        filename=str(path),
    )

    for node in tree.body:
        if not (
            isinstance(node, ast.ClassDef)
            and node.name == class_name
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
                == method_name
            ):
                arguments = (
                    statement.args.posonlyargs
                    + statement.args.args
                    + statement.args.kwonlyargs
                )

                return [
                    argument.arg
                    for argument in arguments
                ]

    raise RuntimeError(
        f"Method {class_name}.{method_name} "
        f"was not found in {path}."
    )


def all_function_parameter_names(
    path: Path,
) -> list[str]:
    tree = ast.parse(
        read_source(path),
        filename=str(path),
    )

    parameters: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            arguments = (
                node.args.posonlyargs
                + node.args.args
                + node.args.kwonlyargs
            )

            parameters.update(
                argument.arg
                for argument in arguments
            )

    return sorted(parameters)


def count_markers(
    source: str,
    markers: list[str],
) -> dict[str, int]:
    return {
        marker: source.lower().count(
            marker.lower()
        )
        for marker in markers
    }


print("=" * 92)
print(
    "MILESTONE 10.7A — VOICE STYLE "
    "CAPABILITY AUDIT AND CONTRACT LOCK"
)
print("=" * 92)

paths = {
    "schemas": (
        BACKEND_ROOT
        / "app"
        / "database"
        / "schemas.py"
    ),
    "models": (
        BACKEND_ROOT
        / "app"
        / "database"
        / "models.py"
    ),
    "speech_api": (
        BACKEND_ROOT
        / "app"
        / "api"
        / "speech.py"
    ),
    "tts_service": (
        BACKEND_ROOT
        / "app"
        / "services"
        / "tts_service.py"
    ),
    "segmented_synthesis": (
        BACKEND_ROOT
        / "app"
        / "services"
        / "segmented_synthesis.py"
    ),
    "segment_router": (
        BACKEND_ROOT
        / "app"
        / "services"
        / "segment_router.py"
    ),
    "engine_router": (
        BACKEND_ROOT
        / "app"
        / "services"
        / "engine_router.py"
    ),
    "cosyvoice_client": (
        BACKEND_ROOT
        / "app"
        / "services"
        / "cosyvoice_engine.py"
    ),
    "indicf5_client": (
        BACKEND_ROOT
        / "app"
        / "services"
        / "f5_engine.py"
    ),
    "cosyvoice_server": (
        BACKEND_ROOT
        / "ai_models"
        / "cosyvoice"
        / "server.py"
    ),
    "indicf5_schema": (
        BACKEND_ROOT
        / "ai_models"
        / "indicf5"
        / "schemas.py"
    ),
    "indicf5_engine": (
        BACKEND_ROOT
        / "ai_models"
        / "indicf5"
        / "engine.py"
    ),
    "frontend": (
        FRONTEND_ROOT
        / "src"
        / "App.jsx"
    ),
}

missing_paths = {
    name: str(path)
    for name, path in paths.items()
    if not path.exists()
}

check(
    "All required style-audit files exist",
    not missing_paths,
    json.dumps(
        missing_paths,
        indent=2,
    ),
)

request_fields = class_field_names(
    paths["schemas"],
    "GenerateSpeechRequest",
)

history_response_fields = class_field_names(
    paths["schemas"],
    "GeneratedAudioResponse",
)

generation_response_fields = class_field_names(
    paths["schemas"],
    "GenerateSpeechResponse",
)

generated_audio_fields = class_field_names(
    paths["models"],
    "GeneratedAudio",
)

tts_parameters = method_parameter_names(
    paths["tts_service"],
    "TTSService",
    "generate_speech",
)

cosyvoice_parameters = method_parameter_names(
    paths["cosyvoice_client"],
    "CosyVoiceEngine",
    "generate",
)

indicf5_parameters = method_parameter_names(
    paths["indicf5_client"],
    "IndicF5Engine",
    "generate",
)

segmented_parameters = (
    all_function_parameter_names(
        paths["segmented_synthesis"]
    )
)

segment_router_parameters = (
    all_function_parameter_names(
        paths["segment_router"]
    )
)

speech_source = read_source(
    paths["speech_api"]
)

frontend_source = read_source(
    paths["frontend"]
)

cosyvoice_server_source = read_source(
    paths["cosyvoice_server"]
)

indicf5_schema_source = read_source(
    paths["indicf5_schema"]
)

indicf5_engine_source = read_source(
    paths["indicf5_engine"]
)

allowed_styles = [
    "neutral",
    "professional",
    "energetic",
    "calm",
    "storytelling",
]

style_contract: dict[str, Any] = {
    "contract_version": "10.7A-v1",
    "field_name": "style",
    "allowed_styles": allowed_styles,
    "default_style": "neutral",
    "compatibility": {
        "omitted_style": "neutral",
        "legacy_history_style": "neutral",
        "invalid_style_http_status": 422,
    },
    "scope": {
        "selection": "one style per generation request",
        "segments": (
            "the same resolved style must be used "
            "for every segment in one request"
        ),
        "fallback": (
            "engine fallback must preserve the "
            "requested style"
        ),
        "hybrid": (
            "hybrid generations must preserve one "
            "request-level style across all engines"
        ),
    },
    "text_contract": {
        "stored_text": (
            "store the user's cleaned source text "
            "without style instructions"
        ),
        "spoken_text": (
            "style implementation must not cause "
            "style instructions to be spoken"
        ),
    },
    "processing_contract": {
        "baseline": (
            "v1 styles must work through an "
            "engine-neutral delivery profile"
        ),
        "native_engine_style": (
            "optional capability enhancement only; "
            "it must not be required for correctness"
        ),
        "controls": (
            "resolve style and explicit user controls "
            "once, then apply final processing once"
        ),
        "joined_audio": (
            "long and hybrid audio must not receive "
            "one style pass per segment plus another "
            "style pass after joining"
        ),
    },
    "persistence_contract": {
        "database_column": "generated_audio.style",
        "nullable": False,
        "default": "neutral",
        "request_response_field": "style",
        "history_response_field": "style",
    },
    "frontend_contract": {
        "control": "single select",
        "default": "neutral",
        "display_in_latest_generation": True,
        "display_in_history": True,
    },
    "style_semantics": {
        "neutral": (
            "original delivery with no intentional "
            "style adjustment"
        ),
        "professional": (
            "steady, controlled and restrained delivery"
        ),
        "energetic": (
            "quicker and more assertive delivery"
        ),
        "calm": (
            "slower, softer and relaxed delivery"
        ),
        "storytelling": (
            "measured, warm and slightly slower delivery"
        ),
    },
    "tuning_policy": {
        "exact_audio_values_locked": False,
        "reason": (
            "speed, gain and tonal values must be "
            "selected through isolated audio comparison"
        ),
        "neutral_values": (
            "neutral must preserve current behaviour"
        ),
    },
}

check(
    "Allowed style names are locked",
    allowed_styles
    == [
        "neutral",
        "professional",
        "energetic",
        "calm",
        "storytelling",
    ],
)

check(
    "Style names are unique",
    len(allowed_styles)
    == len(
        set(allowed_styles)
    ),
)

check(
    "Style names use lowercase API-safe values",
    all(
        re.fullmatch(
            r"[a-z][a-z0-9_]*",
            style,
        )
        is not None
        for style in allowed_styles
    ),
    repr(allowed_styles),
)

check(
    "Neutral is the default style",
    style_contract["default_style"]
    == "neutral",
)

check(
    "Default style is an allowed style",
    style_contract["default_style"]
    in allowed_styles,
)

check(
    "Public API field is locked as style",
    style_contract["field_name"]
    == "style",
)

check(
    "Invalid styles are rejected by schema validation",
    (
        style_contract[
            "compatibility"
        ][
            "invalid_style_http_status"
        ]
        == 422
    ),
)

check(
    "Omitted styles remain backward compatible",
    (
        style_contract[
            "compatibility"
        ][
            "omitted_style"
        ]
        == "neutral"
    ),
)

check(
    "Legacy history migrates to neutral",
    (
        style_contract[
            "compatibility"
        ][
            "legacy_history_style"
        ]
        == "neutral"
    ),
)

check(
    "Style persistence is non-null",
    (
        style_contract[
            "persistence_contract"
        ][
            "nullable"
        ]
        is False
    ),
)

check(
    "Style is preserved across all segments",
    "same resolved style"
    in style_contract[
        "scope"
    ][
        "segments"
    ],
)

check(
    "Fallback must preserve style",
    "preserve"
    in style_contract[
        "scope"
    ][
        "fallback"
    ],
)

check(
    "Style instructions cannot alter stored text",
    "without style instructions"
    in style_contract[
        "text_contract"
    ][
        "stored_text"
    ],
)

check(
    "Style instructions cannot be spoken",
    "must not"
    in style_contract[
        "text_contract"
    ][
        "spoken_text"
    ],
)

check(
    "Final style processing remains single-pass",
    "apply final processing once"
    in style_contract[
        "processing_contract"
    ][
        "controls"
    ],
)

check(
    "V1 has an engine-neutral baseline",
    "engine-neutral"
    in style_contract[
        "processing_contract"
    ][
        "baseline"
    ],
)

# ------------------------------------------------------------
# Current baseline checks
# ------------------------------------------------------------

check(
    "Current request schema has no partial style field",
    "style" not in request_fields,
    repr(request_fields),
)

check(
    "Current history schema has no partial style field",
    "style"
    not in history_response_fields,
    repr(history_response_fields),
)

check(
    "Current database model has no partial style column",
    "style" not in generated_audio_fields,
    repr(generated_audio_fields),
)

check(
    "Current TTS service has no partial style parameter",
    "style" not in tts_parameters,
    repr(tts_parameters),
)

check(
    "Current speech API does not pass request.style",
    "request.style"
    not in speech_source,
)

frontend_style_state = re.search(
    r"const\s*\[\s*style\s*,\s*setStyle\s*\]",
    frontend_source,
)

check(
    "Current frontend has no partial style state",
    frontend_style_state is None,
)

check(
    "Segmented synthesis has no partial style argument",
    "style"
    not in segmented_parameters,
    repr(segmented_parameters),
)

check(
    "Segment router has no partial style argument",
    "style"
    not in segment_router_parameters,
    repr(segment_router_parameters),
)

# ------------------------------------------------------------
# Engine capability audit
# ------------------------------------------------------------

cosyvoice_capability = count_markers(
    cosyvoice_server_source,
    [
        "instruct_text",
        "inference_instruct",
        "inference_zero_shot",
        "emotion",
        "style",
    ],
)

indicf5_capability = {
    "schema_markers": count_markers(
        indicf5_schema_source,
        [
            "instruction",
            "instruct",
            "emotion",
            "style",
        ],
    ),
    "engine_markers": count_markers(
        indicf5_engine_source,
        [
            "instruction",
            "instruct",
            "emotion",
            "style",
        ],
    ),
}

source_hashes = {
    name: {
        "path": str(path),
        "sha256": sha256_file(path),
    }
    for name, path in paths.items()
}

audit_report = {
    "milestone": "10.7A",
    "captured_at": datetime.now().isoformat(),
    "project_root": str(PROJECT_ROOT),
    "backend_root": str(BACKEND_ROOT),
    "current_contract": {
        "request_fields": request_fields,
        "history_response_fields": (
            history_response_fields
        ),
        "generation_response_fields": (
            generation_response_fields
        ),
        "database_fields": generated_audio_fields,
        "tts_parameters": tts_parameters,
        "cosyvoice_parameters": (
            cosyvoice_parameters
        ),
        "indicf5_parameters": (
            indicf5_parameters
        ),
        "segmented_parameters": (
            segmented_parameters
        ),
        "segment_router_parameters": (
            segment_router_parameters
        ),
    },
    "engine_capability_audit": {
        "cosyvoice_server": (
            cosyvoice_capability
        ),
        "indicf5": (
            indicf5_capability
        ),
    },
    "locked_style_contract": style_contract,
    "source_hashes": source_hashes,
}

REPORT_FOLDER.mkdir(
    parents=True,
    exist_ok=True,
)

CONTRACT_PATH.write_text(
    json.dumps(
        style_contract,
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)

AUDIT_PATH.write_text(
    json.dumps(
        audit_report,
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)

check(
    "Locked style contract report was written",
    (
        CONTRACT_PATH.exists()
        and CONTRACT_PATH.stat().st_size
        > 0
    ),
    str(CONTRACT_PATH),
)

check(
    "Capability audit report was written",
    (
        AUDIT_PATH.exists()
        and AUDIT_PATH.stat().st_size
        > 0
    ),
    str(AUDIT_PATH),
)

print()
print("Locked styles:")
for style in allowed_styles:
    print(
        f"  - {style}: "
        f"{style_contract['style_semantics'][style]}"
    )

print()
print("Current request fields:")
print(
    json.dumps(
        request_fields,
        indent=2,
    )
)

print()
print("Current GeneratedAudio fields:")
print(
    json.dumps(
        generated_audio_fields,
        indent=2,
    )
)

print()
print("CosyVoice capability markers:")
print(
    json.dumps(
        cosyvoice_capability,
        indent=2,
    )
)

print()
print("IndicF5 capability markers:")
print(
    json.dumps(
        indicf5_capability,
        indent=2,
    )
)

print()
print("Contract report:", CONTRACT_PATH)
print("Audit report   :", AUDIT_PATH)

print()
print("=" * 92)
print(
    "MILESTONE 10.7A VOICE STYLE "
    "CONTRACT: PASSED"
)
print("=" * 92)
print("Checks passed:", checks_passed)
