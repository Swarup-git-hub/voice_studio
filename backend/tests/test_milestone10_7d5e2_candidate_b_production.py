from __future__ import annotations

import ast
import json
import shutil
import sys
import tempfile
import wave
from array import array
from datetime import datetime
from pathlib import Path
from typing import Any

from app.audio.style_profiles import (
    STYLE_PROFILES,
)
from app.audio.style_profiles import (
    resolve_style_controls,
)
from app.services.tts_service import (
    tts_service,
)


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

COMPARISON_ROOT = (
    BACKEND_ROOT
    / "milestone_reports"
    / "style_comparisons"
)

REPORT_PATH = (
    BACKEND_ROOT
    / "milestone_reports"
    / "milestone10_7d5e2_candidate_b_production.json"
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


def read_wav(
    path: Path,
) -> tuple[
    dict[str, float | int],
    bytes,
]:
    with wave.open(
        str(path),
        "rb",
    ) as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()

        frames = wav_file.readframes(
            frame_count
        )

    metadata: dict[
        str,
        float | int,
    ] = {
        "channels": channels,
        "sample_width": sample_width,
        "sample_rate": sample_rate,
        "frame_count": frame_count,
        "duration_seconds": (
            frame_count
            / sample_rate
        ),
        "file_size": (
            path.stat().st_size
        ),
    }

    return metadata, frames


def clipped_sample_count(
    frame_bytes: bytes,
) -> int:
    samples = array(
        "h"
    )

    samples.frombytes(
        frame_bytes
    )

    if sys.byteorder != "little":
        samples.byteswap()

    return sum(
        1
        for sample in samples
        if abs(
            sample
        )
        >= 32767
    )


print("=" * 92)
print(
    "MILESTONE 10.7D-5E-2 — CANDIDATE B "
    "PRODUCTION INTEGRATION"
)
print("=" * 92)

check(
    "Style profile module exists",
    STYLE_PATH.exists(),
    str(
        STYLE_PATH
    ),
)

check(
    "TTS service module exists",
    TTS_PATH.exists(),
    str(
        TTS_PATH
    ),
)

energetic = STYLE_PROFILES[
    "energetic"
]

check(
    "Energetic speed multiplier is 1.025",
    energetic.speed_multiplier
    == 1.025,
)

check(
    "Energetic volume multiplier is neutral",
    energetic.volume_multiplier
    == 1.0,
)

check(
    "Energetic bass offset is neutral",
    energetic.bass_offset_db
    == 0.0,
)

check(
    "Energetic presence gain is 0.8 dB",
    energetic.presence_gain_db
    == 0.8,
)

check(
    "Energetic presence frequency is 2800 Hz",
    energetic.presence_frequency_hz
    == 2800,
)

check(
    "Energetic presence Q is 1.2",
    energetic.presence_q
    == 1.2,
)

expected_unchanged_profiles: dict[
    str,
    tuple[
        float,
        float,
        float,
    ],
] = {
    "neutral": (
        1.0,
        1.0,
        0.0,
    ),
    "professional": (
        0.98,
        1.0,
        0.5,
    ),
    "calm": (
        0.92,
        0.95,
        -0.5,
    ),
    "storytelling": (
        0.96,
        1.0,
        0.8,
    ),
}

for style_name, expected_values in (
    expected_unchanged_profiles.items()
):
    profile = STYLE_PROFILES[
        style_name
    ]

    actual_values = (
        profile.speed_multiplier,
        profile.volume_multiplier,
        profile.bass_offset_db,
    )

    check(
        f"{style_name} profile remains unchanged",
        actual_values == expected_values,
        (
            f"Expected={expected_values}; "
            f"Actual={actual_values}"
        ),
    )

check(
    "Non-Energetic profiles have no presence boost",
    all(
        STYLE_PROFILES[
            style_name
        ].presence_gain_db
        == 0.0
        for style_name
        in expected_unchanged_profiles
    ),
)

resolved = resolve_style_controls(
    style="energetic",
    speed=1.0,
    volume=1.0,
    bass=0.0,
)

check(
    "Resolved Energetic speed is 1.025",
    resolved.effective_speed
    == 1.025,
)

check(
    "Resolved Energetic volume is 1.0",
    resolved.effective_volume
    == 1.0,
)

check(
    "Resolved Energetic bass is 0.0",
    resolved.effective_bass
    == 0.0,
)

check(
    "Resolved profile preserves presence gain",
    resolved.profile.presence_gain_db
    == 0.8,
)

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

apply_arguments = {
    argument.arg
    for argument in (
        apply_function.args.args
        + apply_function.args.kwonlyargs
    )
}

check(
    "Audio controls accept presence gain",
    "presence_gain_db"
    in apply_arguments,
)

check(
    "Audio controls accept presence frequency",
    "presence_frequency_hz"
    in apply_arguments,
)

check(
    "Audio controls accept presence Q",
    "presence_q"
    in apply_arguments,
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
    "Final call passes presence gain",
    "presence_gain_db"
    in final_keywords,
)

check(
    "Final call passes presence frequency",
    "presence_frequency_hz"
    in final_keywords,
)

check(
    "Final call passes presence Q",
    "presence_q"
    in final_keywords,
)

candidate_folders = [
    folder
    for folder in COMPARISON_ROOT.glob(
        "milestone10_7d5d_*"
    )
    if (
        folder.is_dir()
        and (
            folder
            / "00_neutral_reference.wav"
        ).exists()
        and (
            folder
            / "candidate_b_pace_presence.wav"
        ).exists()
    )
]

candidate_folders.sort(
    key=lambda folder: (
        folder.stat().st_mtime
    ),
    reverse=True,
)

check(
    "Selected Candidate B bake-off folder exists",
    bool(
        candidate_folders
    ),
    str(
        COMPARISON_ROOT
    ),
)

selected_folder = candidate_folders[0]

neutral_source = (
    selected_folder
    / "00_neutral_reference.wav"
)

selected_candidate = (
    selected_folder
    / "candidate_b_pace_presence.wav"
)

check(
    "Neutral bake-off source exists",
    (
        neutral_source.exists()
        and neutral_source.stat().st_size
        > 44
    ),
    str(
        neutral_source
    ),
)

check(
    "Selected Candidate B file exists",
    (
        selected_candidate.exists()
        and selected_candidate.stat().st_size
        > 44
    ),
    str(
        selected_candidate
    ),
)

with tempfile.TemporaryDirectory(
    prefix="milestone10_7d5e2_"
) as temporary_directory:
    temporary_root = Path(
        temporary_directory
    )

    production_input = (
        temporary_root
        / "production_input.wav"
    )

    production_output = (
        temporary_root
        / "production_candidate_b.wav"
    )

    shutil.copy2(
        neutral_source,
        production_input,
    )

    tts_service.apply_audio_controls(
        raw_audio=production_input,
        final_audio=production_output,
        volume=resolved.effective_volume,
        bass=resolved.effective_bass,
        speed=resolved.effective_speed,
        apply_speed=True,
        presence_gain_db=(
            resolved.profile.presence_gain_db
        ),
        presence_frequency_hz=(
            resolved.profile.presence_frequency_hz
        ),
        presence_q=(
            resolved.profile.presence_q
        ),
    )

    check(
        "Production Candidate B output exists",
        (
            production_output.exists()
            and production_output.stat().st_size
            > 44
        ),
        str(
            production_output
        ),
    )

    neutral_metadata, neutral_frames = read_wav(
        neutral_source
    )

    selected_metadata, selected_frames = read_wav(
        selected_candidate
    )

    production_metadata, production_frames = read_wav(
        production_output
    )

    check(
        "Production output is mono",
        production_metadata[
            "channels"
        ]
        == 1,
        repr(
            production_metadata
        ),
    )

    check(
        "Production output is PCM16",
        production_metadata[
            "sample_width"
        ]
        == 2,
        repr(
            production_metadata
        ),
    )

    check(
        "Production output is 24 kHz",
        production_metadata[
            "sample_rate"
        ]
        == 24_000,
        repr(
            production_metadata
        ),
    )

    check(
        "Selected Candidate B is valid 24 kHz mono PCM16",
        (
            selected_metadata[
                "channels"
            ]
            == 1
            and selected_metadata[
                "sample_width"
            ]
            == 2
            and selected_metadata[
                "sample_rate"
            ]
            == 24_000
        ),
        repr(
            selected_metadata
        ),
    )

    check(
        "Production duration matches selected Candidate B",
        abs(
            float(
                production_metadata[
                    "duration_seconds"
                ]
            )
            - float(
                selected_metadata[
                    "duration_seconds"
                ]
            )
        )
        <= 0.01,
        (
            f"Production="
            f"{production_metadata['duration_seconds']}; "
            f"Selected="
            f"{selected_metadata['duration_seconds']}"
        ),
    )

    check(
        "Production PCM matches selected Candidate B",
        production_frames
        == selected_frames,
    )

    check(
        "Production Candidate B differs from Neutral",
        production_frames
        != neutral_frames,
    )

    check(
        "Production does not increase clipped samples",
        clipped_sample_count(
            production_frames
        )
        <= clipped_sample_count(
            neutral_frames
        ),
        (
            "Neutral clipped="
            f"{clipped_sample_count(neutral_frames)}; "
            "Production clipped="
            f"{clipped_sample_count(production_frames)}"
        ),
    )

    report: dict[str, Any] = {
        "milestone": "10.7D-5E-2",
        "created_at": datetime.now().isoformat(),
        "selected_candidate": "B",
        "selected_bakeoff_folder": str(
            selected_folder
        ),
        "neutral_source": str(
            neutral_source
        ),
        "selected_candidate_path": str(
            selected_candidate
        ),
        "production_profile": {
            "speed_multiplier": (
                energetic.speed_multiplier
            ),
            "volume_multiplier": (
                energetic.volume_multiplier
            ),
            "bass_offset_db": (
                energetic.bass_offset_db
            ),
            "presence_gain_db": (
                energetic.presence_gain_db
            ),
            "presence_frequency_hz": (
                energetic.presence_frequency_hz
            ),
            "presence_q": (
                energetic.presence_q
            ),
        },
        "neutral_metadata": neutral_metadata,
        "selected_metadata": selected_metadata,
        "production_metadata": (
            production_metadata
        ),
        "pcm_matches_selected_candidate": (
            production_frames
            == selected_frames
        ),
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
        default=str,
    )
    + "\n",
    encoding="utf-8",
)

check(
    "Production integration report was saved",
    (
        REPORT_PATH.exists()
        and REPORT_PATH.stat().st_size
        > 0
    ),
    str(
        REPORT_PATH
    ),
)

print()
print("=" * 92)
print("LOCKED PRODUCTION ENERGETIC PROFILE")
print("=" * 92)

print(
    json.dumps(
        {
            "speed_multiplier": (
                energetic.speed_multiplier
            ),
            "volume_multiplier": (
                energetic.volume_multiplier
            ),
            "bass_offset_db": (
                energetic.bass_offset_db
            ),
            "presence_gain_db": (
                energetic.presence_gain_db
            ),
            "presence_frequency_hz": (
                energetic.presence_frequency_hz
            ),
            "presence_q": (
                energetic.presence_q
            ),
        },
        indent=2,
    )
)

print()
print(
    "Selected bake-off folder:",
    selected_folder,
)

print()
print("=" * 92)
print(
    "MILESTONE 10.7D-5E-2 CANDIDATE B "
    "PRODUCTION INTEGRATION: PASSED"
)
print("=" * 92)

print(
    "Checks passed:",
    checks_passed,
)

print()
print(
    "Report:",
    REPORT_PATH,
)
