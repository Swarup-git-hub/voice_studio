from __future__ import annotations

import ast
import math
import tempfile
import wave
from array import array
from pathlib import Path

from app.audio.style_profiles import (
    resolve_style_controls,
)
from app.services.tts_service import (
    tts_service,
)


BACKEND_ROOT = Path(__file__).resolve().parents[1]

TTS_PATH = (
    BACKEND_ROOT
    / "app"
    / "services"
    / "tts_service.py"
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


def write_tone(
    path: Path,
    duration_seconds: float = 4.0,
    sample_rate: int = 24_000,
) -> None:
    frame_count = int(
        duration_seconds
        * sample_rate
    )

    samples = array(
        "h",
        (
            int(
                7000
                * math.sin(
                    2.0
                    * math.pi
                    * 440.0
                    * frame_index
                    / sample_rate
                )
            )
            for frame_index
            in range(
                frame_count
            )
        ),
    )

    with wave.open(
        str(path),
        "wb",
    ) as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(
            sample_rate
        )
        wav_file.writeframes(
            samples.tobytes()
        )


def read_metadata(
    path: Path,
) -> dict[str, float | int]:
    with wave.open(
        str(path),
        "rb",
    ) as wav_file:
        frames = wav_file.getnframes()
        sample_rate = wav_file.getframerate()

        return {
            "channels": (
                wav_file.getnchannels()
            ),
            "sample_width": (
                wav_file.getsampwidth()
            ),
            "sample_rate": sample_rate,
            "frames": frames,
            "duration_seconds": (
                frames
                / sample_rate
            ),
        }


print("=" * 92)
print(
    "MILESTONE 10.7D-5A — ROLE-BASED "
    "DETERMINISTIC STYLE SPEED"
)
print("=" * 92)

source = TTS_PATH.read_text(
    encoding="utf-8-sig"
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

check(
    "TTS generation method exists",
    generate_method is not None,
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

check(
    "Exactly one requested-control validation exists",
    len(
        requested_validation
    )
    == 1,
    repr(
        [
            call.lineno
            for call
            in requested_validation
        ]
    ),
)

check(
    "Exactly one effective-control validation exists",
    len(
        effective_validation
    )
    == 1,
    repr(
        [
            call.lineno
            for call
            in effective_validation
        ]
    ),
)

requested_keywords = keyword_map(
    requested_validation[0]
)

effective_keywords = keyword_map(
    effective_validation[0]
)

check(
    "Requested validation uses requested speed",
    is_name(
        requested_keywords.get(
            "speed"
        ),
        "speed",
    ),
)

check(
    "Effective validation uses effective speed",
    is_name(
        effective_keywords.get(
            "speed"
        ),
        "effective_speed",
    ),
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

check(
    "Exactly one routing_result assignment exists",
    len(
        routing_assignments
    )
    == 1,
    repr(
        [
            assignment.lineno
            for assignment
            in routing_assignments
        ]
    ),
)

routing_calls = [
    node
    for node in ast.walk(
        routing_assignments[0].value
    )
    if isinstance(
        node,
        ast.Call,
    )
]

synthesis_candidates = []

for call in routing_calls:
    keywords = keyword_map(
        call
    )

    for speed_keyword in (
        "speed",
        "synthesis_speed",
        "requested_speed",
    ):
        if speed_keyword in keywords:
            synthesis_candidates.append(
                (
                    call,
                    speed_keyword,
                    keywords[
                        speed_keyword
                    ],
                )
            )

check(
    "Exactly one routing synthesis speed exists",
    len(
        synthesis_candidates
    )
    == 1,
    repr(
        [
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
    ),
)

synthesis_call, synthesis_keyword, synthesis_value = (
    synthesis_candidates[0]
)

check(
    "Routing synthesis uses native 1.0 speed",
    is_number(
        synthesis_value,
        1.0,
    ),
    ast.dump(
        synthesis_value
    ),
)

check(
    "Routing synthesis call is not validate_controls",
    call_name(
        synthesis_call
    )
    != "validate_controls",
    call_name(
        synthesis_call
    ),
)

final_calls = [
    call
    for call in calls
    if call_name(
        call
    )
    == "apply_audio_controls"
]

check(
    "Exactly one final audio-control call exists",
    len(
        final_calls
    )
    == 1,
)

final_keywords = keyword_map(
    final_calls[0]
)

check(
    "Final processing uses effective speed",
    is_name(
        final_keywords.get(
            "speed"
        ),
        "effective_speed",
    ),
)

check(
    "Final processing uses effective volume",
    is_name(
        final_keywords.get(
            "volume"
        ),
        "effective_volume",
    ),
)

check(
    "Final processing uses effective bass",
    is_name(
        final_keywords.get(
            "bass"
        ),
        "effective_bass",
    ),
)

apply_speed_value = final_keywords.get(
    "apply_speed"
)

check(
    "Final processing forces apply_speed True",
    (
        isinstance(
            apply_speed_value,
            ast.Constant,
        )
        and apply_speed_value.value
        is True
    ),
    (
        ast.dump(
            apply_speed_value
        )
        if apply_speed_value
        is not None
        else "Missing"
    ),
)

neutral_controls = resolve_style_controls(
    style="neutral",
    speed=1.0,
    volume=1.0,
    bass=0.0,
)

energetic_controls = resolve_style_controls(
    style="energetic",
    speed=1.0,
    volume=1.0,
    bass=0.0,
)

check(
    "Neutral effective speed is 1.0",
    neutral_controls.effective_speed
    == 1.0,
)

check(
    "Energetic effective speed is 1.08",
    energetic_controls.effective_speed
    == 1.08,
)

metadata = {}

audio_bytes = {}

with tempfile.TemporaryDirectory(
    prefix="milestone10_7d5a_role_"
) as temporary_directory:
    temporary_root = Path(
        temporary_directory
    )

    for style_name, controls in (
        (
            "neutral",
            neutral_controls,
        ),
        (
            "energetic",
            energetic_controls,
        ),
    ):
        raw_path = (
            temporary_root
            / f"{style_name}_raw.wav"
        )

        final_path = (
            temporary_root
            / f"{style_name}_final.wav"
        )

        write_tone(
            raw_path
        )

        tts_service.apply_audio_controls(
            raw_audio=raw_path,
            final_audio=final_path,
            volume=(
                controls
                .effective_volume
            ),
            bass=(
                controls
                .effective_bass
            ),
            speed=(
                controls
                .effective_speed
            ),
            apply_speed=True,
        )

        check(
            f"{style_name} processed output exists",
            (
                final_path.exists()
                and final_path.stat().st_size
                > 44
            ),
            str(
                final_path
            ),
        )

        metadata[
            style_name
        ] = read_metadata(
            final_path
        )

        audio_bytes[
            style_name
        ] = final_path.read_bytes()

check(
    "Both outputs are mono",
    all(
        item["channels"] == 1
        for item
        in metadata.values()
    ),
    repr(
        metadata
    ),
)

check(
    "Both outputs are PCM16",
    all(
        item["sample_width"] == 2
        for item
        in metadata.values()
    ),
    repr(
        metadata
    ),
)

check(
    "Both outputs are 24 kHz",
    all(
        item["sample_rate"] == 24_000
        for item
        in metadata.values()
    ),
    repr(
        metadata
    ),
)

neutral_duration = float(
    metadata[
        "neutral"
    ][
        "duration_seconds"
    ]
)

energetic_duration = float(
    metadata[
        "energetic"
    ][
        "duration_seconds"
    ]
)

check(
    "Neutral remains approximately four seconds",
    3.9
    <= neutral_duration
    <= 4.1,
    repr(
        metadata[
            "neutral"
        ]
    ),
)

check(
    "Energetic is deterministically shorter",
    energetic_duration
    < neutral_duration,
    repr(
        metadata
    ),
)

expected_energetic_duration = (
    neutral_duration
    / energetic_controls.effective_speed
)

check(
    "Energetic duration matches 1.08 speed",
    abs(
        energetic_duration
        - expected_energetic_duration
    )
    <= 0.08,
    (
        f"Expected≈"
        f"{expected_energetic_duration:.3f}; "
        f"Actual="
        f"{energetic_duration:.3f}"
    ),
)

check(
    "Energetic audio differs from Neutral",
    audio_bytes[
        "energetic"
    ]
    != audio_bytes[
        "neutral"
    ],
)

print()
print(
    "Routing synthesis call:",
    call_name(
        synthesis_call
    ),
)

print(
    "Routing synthesis line:",
    synthesis_call.lineno,
)

print(
    "Routing speed keyword:",
    synthesis_keyword,
)

print()
print("Deterministic comparison:")

print(
    "  Neutral  :",
    f"{neutral_duration:.3f}s",
)

print(
    "  Energetic:",
    f"{energetic_duration:.3f}s",
)

print()
print("=" * 92)
print(
    "MILESTONE 10.7D-5A ROLE-BASED "
    "DETERMINISTIC STYLE SPEED: PASSED"
)
print("=" * 92)

print(
    "Checks passed:",
    checks_passed,
)
