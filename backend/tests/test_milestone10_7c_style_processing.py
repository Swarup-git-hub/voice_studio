from __future__ import annotations

import math
import tempfile
import wave
from array import array
from pathlib import Path

from app.audio.style_profiles import (
    MAX_BASS_DB,
    MAX_SPEED,
    MAX_VOLUME,
    MIN_BASS_DB,
    MIN_SPEED,
    MIN_VOLUME,
    STYLE_PROFILES,
    resolve_style_controls,
)
from app.services.tts_service import (
    TTSService,
    tts_service,
)


BACKEND_ROOT = Path(__file__).resolve().parents[1]

TTS_PATH = (
    BACKEND_ROOT
    / "app"
    / "services"
    / "tts_service.py"
)

EXPECTED_STYLES = {
    "neutral",
    "professional",
    "energetic",
    "calm",
    "storytelling",
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


def write_test_tone(
    path: Path,
    duration_seconds: float = 3.0,
    sample_rate: int = 24_000,
    frequency: float = 440.0,
) -> None:
    frame_count = int(
        duration_seconds
        * sample_rate
    )

    samples = array(
        "h",
        (
            int(
                8000
                * math.sin(
                    2.0
                    * math.pi
                    * frequency
                    * frame_index
                    / sample_rate
                )
            )
            for frame_index
            in range(frame_count)
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


def read_wav_metadata(
    path: Path,
) -> dict[str, float | int]:
    with wave.open(
        str(path),
        "rb",
    ) as wav_file:
        frame_count = (
            wav_file.getnframes()
        )

        sample_rate = (
            wav_file.getframerate()
        )

        return {
            "channels": (
                wav_file.getnchannels()
            ),
            "sample_width": (
                wav_file.getsampwidth()
            ),
            "sample_rate": sample_rate,
            "frames": frame_count,
            "duration_seconds": (
                frame_count
                / sample_rate
            ),
        }


print("=" * 92)
print(
    "MILESTONE 10.7C — STYLE PROFILE "
    "AND AUDIO PROCESSING CONTRACT"
)
print("=" * 92)

check(
    "Exactly five locked profiles exist",
    set(
        STYLE_PROFILES
    )
    == EXPECTED_STYLES,
    repr(
        set(
            STYLE_PROFILES
        )
    ),
)

expected_profiles = {
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
    "energetic": (
        1.08,
        1.05,
        1.0,
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

for style_name in (
    "neutral",
    "professional",
    "energetic",
    "calm",
    "storytelling",
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
        f"{style_name} profile values are locked",
        actual_values
        == expected_profiles[
            style_name
        ],
        repr(actual_values),
    )

neutral = resolve_style_controls(
    style="neutral",
    speed=1.1,
    volume=1.2,
    bass=2.0,
)

check(
    "Neutral preserves requested controls",
    (
        neutral.effective_speed
        == 1.1
        and neutral.effective_volume
        == 1.2
        and neutral.effective_bass
        == 2.0
    ),
    repr(neutral),
)

energetic = resolve_style_controls(
    style="energetic",
    speed=1.0,
    volume=1.0,
    bass=0.0,
)

check(
    "Energetic increases speed",
    energetic.effective_speed
    == 1.08,
)

check(
    "Energetic increases volume",
    energetic.effective_volume
    == 1.05,
)

check(
    "Energetic increases bass",
    energetic.effective_bass
    == 1.0,
)

calm = resolve_style_controls(
    style="calm",
    speed=1.0,
    volume=1.0,
    bass=0.0,
)

check(
    "Calm lowers speed",
    calm.effective_speed
    == 0.92,
)

check(
    "Calm lowers volume",
    calm.effective_volume
    == 0.95,
)

check(
    "Calm softens bass",
    calm.effective_bass
    == -0.5,
)

storytelling = resolve_style_controls(
    style="storytelling",
    speed=1.0,
    volume=1.0,
    bass=0.0,
)

check(
    "Storytelling uses measured speed",
    storytelling.effective_speed
    == 0.96,
)

composed = resolve_style_controls(
    style="energetic",
    speed=1.2,
    volume=1.1,
    bass=2.0,
)

check(
    "Style composes with requested speed",
    composed.effective_speed
    == 1.296,
    repr(composed),
)

check(
    "Style composes with requested volume",
    composed.effective_volume
    == 1.155,
    repr(composed),
)

check(
    "Style composes with requested bass",
    composed.effective_bass
    == 3.0,
    repr(composed),
)

upper = resolve_style_controls(
    style="energetic",
    speed=2.0,
    volume=3.0,
    bass=20.0,
)

check(
    "Effective speed respects upper limit",
    upper.effective_speed
    == MAX_SPEED,
)

check(
    "Effective volume respects upper limit",
    upper.effective_volume
    == MAX_VOLUME,
)

check(
    "Effective bass respects upper limit",
    upper.effective_bass
    == MAX_BASS_DB,
)

lower = resolve_style_controls(
    style="calm",
    speed=0.5,
    volume=0.1,
    bass=-20.0,
)

check(
    "Effective speed respects lower limit",
    lower.effective_speed
    == MIN_SPEED,
)

check(
    "Effective volume respects lower limit",
    lower.effective_volume
    == MIN_VOLUME,
)

check(
    "Effective bass respects lower limit",
    lower.effective_bass
    == MIN_BASS_DB,
)

invalid_style_rejected = False

try:
    resolve_style_controls(
        style="angry",
        speed=1.0,
        volume=1.0,
        bass=0.0,
    )
except ValueError:
    invalid_style_rejected = True

check(
    "Unknown style is rejected",
    invalid_style_rejected,
)

check(
    "TTS style set matches profile registry",
    TTSService.ALLOWED_STYLES
    == EXPECTED_STYLES,
    repr(
        TTSService.ALLOWED_STYLES
    ),
)

tts_source = TTS_PATH.read_text(
    encoding="utf-8-sig"
)

generation_start = tts_source.find(
    "    def generate_speech("
)

generation_source = tts_source[
    generation_start:
]

check(
    "TTS imports the style resolver",
    (
        "from app.audio.style_profiles "
        "import resolve_style_controls"
        in tts_source
    ),
)

check(
    "Style is resolved exactly once per request",
    generation_source.count(
        "style_controls = resolve_style_controls("
    )
    == 1,
)

check(
    "Effective speed reaches synthesis and processing",
    generation_source.count(
        "speed=effective_speed"
    )
    >= 2,
    (
        "Occurrences="
        f"{generation_source.count('speed=effective_speed')}"
    ),
)

effective_control_block = '''            self.apply_audio_controls(
                raw_audio=raw_output_path,
                final_audio=final_output_path,
                volume=effective_volume,
                bass=effective_bass,
                speed=effective_speed,
'''

check(
    "Final processing uses effective volume",
    "volume=effective_volume"
    in effective_control_block
    and effective_control_block
    in generation_source,
)

check(
    "Final processing uses effective bass",
    "bass=effective_bass"
    in effective_control_block
    and effective_control_block
    in generation_source,
)

check(
    "Final processing uses effective speed",
    "speed=effective_speed"
    in effective_control_block
    and effective_control_block
    in generation_source,
)

check(
    "History preserves requested speed",
    "                speed=speed,"
    in generation_source,
)

check(
    "History preserves requested volume",
    "                volume=volume,"
    in generation_source,
)

check(
    "History preserves requested bass",
    "                bass=bass,"
    in generation_source,
)

check(
    "History persists the requested style",
    "                style=clean_style,"
    in generation_source,
)

audio_metadata: dict[
    str,
    dict[str, float | int],
] = {}

audio_bytes: dict[
    str,
    bytes,
] = {}

with tempfile.TemporaryDirectory(
    prefix="milestone10_7c_"
) as temporary_directory:
    temp_root = Path(
        temporary_directory
    )

    for style_name in sorted(
        EXPECTED_STYLES
    ):
        resolution = (
            resolve_style_controls(
                style=style_name,
                speed=1.0,
                volume=1.0,
                bass=0.0,
            )
        )

        raw_path = (
            temp_root
            / f"{style_name}_raw.wav"
        )

        final_path = (
            temp_root
            / f"{style_name}_final.wav"
        )

        write_test_tone(
            raw_path
        )

        tts_service.apply_audio_controls(
            raw_audio=raw_path,
            final_audio=final_path,
            volume=(
                resolution
                .effective_volume
            ),
            bass=(
                resolution
                .effective_bass
            ),
            speed=(
                resolution
                .effective_speed
            ),
            apply_speed=True,
        )

        audio_metadata[
            style_name
        ] = read_wav_metadata(
            final_path
        )

        audio_bytes[
            style_name
        ] = final_path.read_bytes()

        raw_path.unlink(
            missing_ok=True
        )

    check(
        "All five processed outputs exist",
        all(
            (
                temp_root
                / f"{style_name}_final.wav"
            ).exists()
            for style_name
            in EXPECTED_STYLES
        ),
    )

    check(
        "All processed outputs are non-empty",
        all(
            len(
                audio_bytes[
                    style_name
                ]
            )
            > 44
            for style_name
            in EXPECTED_STYLES
        ),
    )

check(
    "All style outputs are mono",
    all(
        metadata["channels"] == 1
        for metadata
        in audio_metadata.values()
    ),
    repr(audio_metadata),
)

check(
    "All style outputs are PCM16",
    all(
        metadata["sample_width"] == 2
        for metadata
        in audio_metadata.values()
    ),
    repr(audio_metadata),
)

check(
    "All style outputs are 24 kHz",
    all(
        metadata["sample_rate"]
        == 24_000
        for metadata
        in audio_metadata.values()
    ),
    repr(audio_metadata),
)

check(
    "All style outputs contain audio frames",
    all(
        metadata["frames"] > 0
        for metadata
        in audio_metadata.values()
    ),
    repr(audio_metadata),
)

neutral_duration = float(
    audio_metadata[
        "neutral"
    ][
        "duration_seconds"
    ]
)

check(
    "Neutral preserves approximately three seconds",
    2.9
    <= neutral_duration
    <= 3.1,
    repr(audio_metadata["neutral"]),
)

check(
    "Energetic output is shorter than neutral",
    (
        audio_metadata[
            "energetic"
        ][
            "duration_seconds"
        ]
        < neutral_duration
    ),
    repr(audio_metadata),
)

check(
    "Professional output is longer than neutral",
    (
        audio_metadata[
            "professional"
        ][
            "duration_seconds"
        ]
        > neutral_duration
    ),
    repr(audio_metadata),
)

check(
    "Calm output is longer than neutral",
    (
        audio_metadata[
            "calm"
        ][
            "duration_seconds"
        ]
        > neutral_duration
    ),
    repr(audio_metadata),
)

check(
    "Storytelling output is longer than neutral",
    (
        audio_metadata[
            "storytelling"
        ][
            "duration_seconds"
        ]
        > neutral_duration
    ),
    repr(audio_metadata),
)

check(
    "Every non-neutral profile changes the audio",
    all(
        audio_bytes[
            style_name
        ]
        != audio_bytes[
            "neutral"
        ]
        for style_name
        in EXPECTED_STYLES
        if style_name
        != "neutral"
    ),
)

print()
print("Resolved profile durations:")

for style_name in sorted(
    audio_metadata
):
    print(
        f"  {style_name:14s}: "
        f"{audio_metadata[style_name]['duration_seconds']:.3f}s"
    )

print()
print("=" * 92)
print(
    "MILESTONE 10.7C STYLE PROFILE "
    "AND AUDIO PROCESSING: PASSED"
)
print("=" * 92)
print("Checks passed:", checks_passed)
