from __future__ import annotations

import re
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]

TTS_PATH = (
    BACKEND_ROOT
    / "app"
    / "services"
    / "tts_service.py"
)


def read_source(
    path: Path,
) -> str:
    return path.read_text(
        encoding="utf-8-sig",
    )


def write_source(
    path: Path,
    source: str,
) -> None:
    path.write_text(
        source,
        encoding="utf-8",
    )


def replace_once(
    source: str,
    old: str,
    new: str,
    label: str,
) -> str:
    count = source.count(old)

    if count != 1:
        raise RuntimeError(
            f"{label}: expected exactly one "
            f"occurrence, found {count}."
        )

    return source.replace(
        old,
        new,
        1,
    )


source = read_source(
    TTS_PATH
)


# ============================================================
# Import profile resolver
# ============================================================

style_import = (
    "from app.audio.style_profiles import "
    "resolve_style_controls\n"
)

if style_import not in source:
    source = replace_once(
        source,
        "from app.core.config import settings\n",
        (
            "from app.core.config import settings\n"
            + style_import
        ),
        "Insert style resolver import",
    )


# ============================================================
# Locate active generation method
# ============================================================

generation_start = source.find(
    "    def generate_speech("
)

if generation_start < 0:
    raise RuntimeError(
        "TTSService.generate_speech was not found."
    )

generation_source = source[
    generation_start:
]


# ============================================================
# Resolve style once after validating requested controls
# ============================================================

if (
    "style_controls = resolve_style_controls("
    not in generation_source
):
    validation_block = '''        self.validate_controls(
            speed=speed,
            volume=volume,
            bass=bass,
        )
'''

    resolution_block = '''        self.validate_controls(
            speed=speed,
            volume=volume,
            bass=bass,
        )

        style_controls = resolve_style_controls(
            style=clean_style,
            speed=speed,
            volume=volume,
            bass=bass,
        )

        effective_speed = (
            style_controls.effective_speed
        )

        effective_volume = (
            style_controls.effective_volume
        )

        effective_bass = (
            style_controls.effective_bass
        )

        self.validate_controls(
            speed=effective_speed,
            volume=effective_volume,
            bass=effective_bass,
        )

        print("\\nSTYLE PROFILE")
        print("-" * 80)
        print("Style            :", clean_style)
        print("Requested Speed  :", speed)
        print("Effective Speed  :", effective_speed)
        print("Requested Volume :", volume)
        print("Effective Volume :", effective_volume)
        print("Requested Bass   :", bass)
        print("Effective Bass   :", effective_bass)
'''

    generation_source = replace_once(
        generation_source,
        validation_block,
        resolution_block,
        "Insert style resolution",
    )


# ============================================================
# Pass effective speed to active synthesis coordinator/router
# ============================================================

if (
    generation_source.count(
        "speed=effective_speed"
    )
    < 1
):
    call_marker_index = -1

    for marker in (
        "CALLING SEGMENTED SYNTHESIS",
        "CALLING ENGINE ROUTER",
    ):
        candidate_index = (
            generation_source.find(
                marker
            )
        )

        if candidate_index >= 0:
            call_marker_index = candidate_index
            break

    if call_marker_index < 0:
        raise RuntimeError(
            "The active synthesis-call marker "
            "was not found."
        )

    controls_marker_index = (
        generation_source.find(
            "# Apply shared controls exactly once",
            call_marker_index,
        )
    )

    if controls_marker_index < 0:
        raise RuntimeError(
            "The shared-controls marker "
            "was not found."
        )

    call_slice = generation_source[
        call_marker_index:
        controls_marker_index
    ]

    speed_pattern = re.compile(
        r"(?m)^(?P<indent>\s*)"
        r"speed=speed,\s*$"
    )

    matches = list(
        speed_pattern.finditer(
            call_slice
        )
    )

    if len(matches) != 1:
        raise RuntimeError(
            "Expected exactly one synthesis "
            "speed argument, found "
            f"{len(matches)}."
        )

    call_slice = speed_pattern.sub(
        lambda match: (
            match.group("indent")
            + "speed=effective_speed,"
        ),
        call_slice,
        count=1,
    )

    generation_source = (
        generation_source[
            :call_marker_index
        ]
        + call_slice
        + generation_source[
            controls_marker_index:
        ]
    )


# ============================================================
# Apply effective style controls once to final audio
# ============================================================

old_controls_block = '''            self.apply_audio_controls(
                raw_audio=raw_output_path,
                final_audio=final_output_path,
                volume=volume,
                bass=bass,
                speed=speed,
'''

new_controls_block = '''            self.apply_audio_controls(
                raw_audio=raw_output_path,
                final_audio=final_output_path,
                volume=effective_volume,
                bass=effective_bass,
                speed=effective_speed,
'''

if new_controls_block not in generation_source:
    generation_source = replace_once(
        generation_source,
        old_controls_block,
        new_controls_block,
        "Apply effective style controls",
    )


source = (
    source[:generation_start]
    + generation_source
)

write_source(
    TTS_PATH,
    source,
)

updated = read_source(
    TTS_PATH
)

required_markers = [
    style_import.strip(),
    "style_controls = resolve_style_controls(",
    "effective_speed = (",
    "effective_volume = (",
    "effective_bass = (",
    "volume=effective_volume",
    "bass=effective_bass",
    "speed=effective_speed",
    "style=clean_style",
]

for marker in required_markers:
    if marker not in updated:
        raise RuntimeError(
            f"Missing style integration marker: "
            f"{marker}"
        )

print(
    "Milestone 10.7C style processing "
    "integration: APPLIED"
)
