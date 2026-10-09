from __future__ import annotations

import json
import math
import subprocess
import sys
import wave
from array import array
from datetime import datetime
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]

SOURCE_PATH = (
    BACKEND_ROOT
    / "milestone_reports"
    / "style_comparisons"
    / "milestone10_7d5b_20260725_233658"
    / "neutral_same_source.wav"
)

OUTPUT_ROOT = (
    BACKEND_ROOT
    / "milestone_reports"
    / "style_comparisons"
)

TIMESTAMP = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

OUTPUT_FOLDER = (
    OUTPUT_ROOT
    / f"milestone10_7d5d_{TIMESTAMP}"
)

REPORT_PATH = (
    OUTPUT_FOLDER
    / "energetic_bakeoff_report.json"
)

CANDIDATES: dict[
    str,
    dict[str, Any],
] = {
    "candidate_a_gentle_pace": {
        "display_name": (
            "Candidate A — Gentle pace"
        ),
        "speed": 1.020,
        "filter": (
            "atempo=1.0200"
        ),
        "description": (
            "Two percent quicker with no tonal "
            "or loudness processing."
        ),
    },
    "candidate_b_pace_presence": {
        "display_name": (
            "Candidate B — Pace and presence"
        ),
        "speed": 1.025,
        "filter": (
            "atempo=1.0250,"
            "equalizer="
            "f=2800:"
            "t=q:"
            "w=1.2:"
            "g=0.8"
        ),
        "description": (
            "Slightly quicker with a mild "
            "clarity and presence lift."
        ),
    },
    "candidate_c_gentle_dynamics": {
        "display_name": (
            "Candidate C — Gentle dynamics"
        ),
        "speed": 1.030,
        "filter": (
            "atempo=1.0300,"
            "equalizer="
            "f=2800:"
            "t=q:"
            "w=1.2:"
            "g=1.0,"
            "acompressor="
            "threshold=0.20:"
            "ratio=1.5:"
            "attack=25:"
            "release=200:"
            "makeup=1.0"
        ),
        "description": (
            "Three percent quicker with mild "
            "presence and gentle compression."
        ),
    },
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

        raise AssertionError(
            message
        )

    checks_passed += 1

    print(
        f"{name}: PASSED"
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

        frame_bytes = wav_file.readframes(
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

    return metadata, frame_bytes


def analyse_pcm16(
    frame_bytes: bytes,
) -> dict[str, float | int]:
    samples = array(
        "h"
    )

    samples.frombytes(
        frame_bytes
    )

    if sys.byteorder != "little":
        samples.byteswap()

    if not samples:
        return {
            "sample_count": 0,
            "peak": 0,
            "peak_ratio": 0.0,
            "rms": 0.0,
            "clipped_samples": 0,
        }

    peak = max(
        abs(
            sample
        )
        for sample in samples
    )

    squared_total = sum(
        sample * sample
        for sample in samples
    )

    rms = math.sqrt(
        squared_total
        / len(
            samples
        )
    )

    clipped_samples = sum(
        1
        for sample in samples
        if abs(
            sample
        )
        >= 32767
    )

    return {
        "sample_count": len(
            samples
        ),
        "peak": peak,
        "peak_ratio": (
            peak
            / 32767.0
        ),
        "rms": rms,
        "clipped_samples": (
            clipped_samples
        ),
    }


def generate_candidate(
    *,
    source: Path,
    destination: Path,
    filter_chain: str,
) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(
            source
        ),
        "-af",
        filter_chain,
        "-ar",
        "24000",
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        str(
            destination
        ),
    ]

    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )

    except subprocess.CalledProcessError as error:
        ffmpeg_error = (
            error.stderr.strip()
            if error.stderr
            else "Unknown FFmpeg error."
        )

        destination.unlink(
            missing_ok=True
        )

        raise RuntimeError(
            "Could not generate Energetic "
            "bake-off candidate.\n"
            f"Candidate: {destination.name}\n"
            f"Filter: {filter_chain}\n"
            f"FFmpeg error: {ffmpeg_error}"
        ) from error


print("=" * 92)
print(
    "MILESTONE 10.7D-5D — CREATOR-QUALITY "
    "ENERGETIC BAKE-OFF"
)
print("=" * 92)

check(
    "Neutral source exists",
    (
        SOURCE_PATH.exists()
        and SOURCE_PATH.is_file()
        and SOURCE_PATH.stat().st_size
        > 44
    ),
    str(
        SOURCE_PATH
    ),
)

OUTPUT_FOLDER.mkdir(
    parents=True,
    exist_ok=True,
)

neutral_copy = (
    OUTPUT_FOLDER
    / "00_neutral_reference.wav"
)

neutral_copy.write_bytes(
    SOURCE_PATH.read_bytes()
)

source_metadata, source_bytes = read_wav(
    neutral_copy
)

source_analysis = analyse_pcm16(
    source_bytes
)

check(
    "Neutral source is mono",
    source_metadata[
        "channels"
    ]
    == 1,
    repr(
        source_metadata
    ),
)

check(
    "Neutral source is PCM16",
    source_metadata[
        "sample_width"
    ]
    == 2,
    repr(
        source_metadata
    ),
)

check(
    "Neutral source is 24 kHz",
    source_metadata[
        "sample_rate"
    ]
    == 24_000,
    repr(
        source_metadata
    ),
)

check(
    "Neutral source has meaningful duration",
    source_metadata[
        "duration_seconds"
    ]
    > 1.0,
    repr(
        source_metadata
    ),
)

results: dict[
    str,
    dict[str, Any],
] = {}

candidate_audio_bytes: list[
    bytes
] = []

for candidate_name, profile in (
    CANDIDATES.items()
):
    print()
    print("-" * 92)
    print(
        profile[
            "display_name"
        ]
    )
    print("-" * 92)

    destination = (
        OUTPUT_FOLDER
        / f"{candidate_name}.wav"
    )

    generate_candidate(
        source=neutral_copy,
        destination=destination,
        filter_chain=profile[
            "filter"
        ],
    )

    check(
        (
            profile[
                "display_name"
            ]
            + " output exists"
        ),
        (
            destination.exists()
            and destination.is_file()
            and destination.stat().st_size
            > 44
        ),
        str(
            destination
        ),
    )

    metadata, audio_bytes = read_wav(
        destination
    )

    analysis = analyse_pcm16(
        audio_bytes
    )

    check(
        (
            profile[
                "display_name"
            ]
            + " is mono"
        ),
        metadata[
            "channels"
        ]
        == 1,
        repr(
            metadata
        ),
    )

    check(
        (
            profile[
                "display_name"
            ]
            + " is PCM16"
        ),
        metadata[
            "sample_width"
        ]
        == 2,
        repr(
            metadata
        ),
    )

    check(
        (
            profile[
                "display_name"
            ]
            + " is 24 kHz"
        ),
        metadata[
            "sample_rate"
        ]
        == 24_000,
        repr(
            metadata
        ),
    )

    source_duration = float(
        source_metadata[
            "duration_seconds"
        ]
    )

    candidate_duration = float(
        metadata[
            "duration_seconds"
        ]
    )

    check(
        (
            profile[
                "display_name"
            ]
            + " is shorter than Neutral"
        ),
        candidate_duration
        < source_duration,
        (
            f"Neutral={source_duration:.3f}; "
            f"Candidate={candidate_duration:.3f}"
        ),
    )

    expected_duration = (
        source_duration
        / float(
            profile[
                "speed"
            ]
        )
    )

    check(
        (
            profile[
                "display_name"
            ]
            + " duration matches its speed"
        ),
        abs(
            candidate_duration
            - expected_duration
        )
        <= 0.10,
        (
            f"Expected≈{expected_duration:.3f}; "
            f"Actual={candidate_duration:.3f}"
        ),
    )

    check(
        (
            profile[
                "display_name"
            ]
            + " does not increase clipping"
        ),
        analysis[
            "clipped_samples"
        ]
        <= source_analysis[
            "clipped_samples"
        ],
        (
            "Source clipped samples="
            f"{source_analysis['clipped_samples']}; "
            "Candidate clipped samples="
            f"{analysis['clipped_samples']}"
        ),
    )

    check(
        (
            profile[
                "display_name"
            ]
            + " differs from Neutral"
        ),
        audio_bytes
        != source_bytes,
    )

    candidate_audio_bytes.append(
        audio_bytes
    )

    results[
        candidate_name
    ] = {
        **profile,
        "path": str(
            destination
        ),
        "metadata": metadata,
        "analysis": analysis,
    }

    print(
        "Duration:",
        f"{candidate_duration:.3f}s",
    )

    print(
        "Peak ratio:",
        f"{float(analysis['peak_ratio']):.4f}",
    )

    print(
        "Clipped samples:",
        analysis[
            "clipped_samples"
        ],
    )

check(
    "All candidate outputs are unique",
    len(
        set(
            candidate_audio_bytes
        )
    )
    == len(
        candidate_audio_bytes
    ),
)

report = {
    "milestone": "10.7D-5D",
    "created_at": (
        datetime.now().isoformat()
    ),
    "purpose": (
        "Offline creator-quality Energetic "
        "profile bake-off."
    ),
    "neutral": {
        "path": str(
            neutral_copy
        ),
        "metadata": source_metadata,
        "analysis": source_analysis,
    },
    "candidates": results,
    "listening_order": [
        "00_neutral_reference.wav",
        "candidate_a_gentle_pace.wav",
        "candidate_b_pace_presence.wav",
        "candidate_c_gentle_dynamics.wav",
    ],
}

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
    "Bake-off report was saved",
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
print(
    "MILESTONE 10.7D-5D ENERGETIC "
    "BAKE-OFF: PASSED"
)
print("=" * 92)

print(
    "Checks passed:",
    checks_passed,
)

print()
print(
    "Bake-off folder:",
    OUTPUT_FOLDER,
)
