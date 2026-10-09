from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


MIN_SPEED = 0.5
MAX_SPEED = 2.0

MIN_VOLUME = 0.1
MAX_VOLUME = 3.0

MIN_BASS_DB = -20.0
MAX_BASS_DB = 20.0


@dataclass(
    frozen=True,
    slots=True,
)
class StyleProfile:
    name: str
    description: str
    speed_multiplier: float
    volume_multiplier: float
    bass_offset_db: float


    presence_gain_db: float = 0.0
    presence_frequency_hz: int = 2800
    presence_q: float = 1.2
@dataclass(
    frozen=True,
    slots=True,
)
class ResolvedStyleControls:
    style: str

    requested_speed: float
    requested_volume: float
    requested_bass: float

    effective_speed: float
    effective_volume: float
    effective_bass: float

    profile: StyleProfile


_STYLE_PROFILES = {
    "neutral": StyleProfile(
        name="neutral",
        description=(
            "Original delivery without intentional "
            "style adjustment."
        ),
        speed_multiplier=1.0,
        volume_multiplier=1.0,
        bass_offset_db=0.0,
    ),
    "professional": StyleProfile(
        name="professional",
        description=(
            "Steady, controlled and restrained delivery."
        ),
        speed_multiplier=0.98,
        volume_multiplier=1.0,
        bass_offset_db=0.5,
    ),
    "energetic": StyleProfile(
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
    ),
    "calm": StyleProfile(
        name="calm",
        description=(
            "Slower, softer and relaxed delivery."
        ),
        speed_multiplier=0.92,
        volume_multiplier=0.95,
        bass_offset_db=-0.5,
    ),
    "storytelling": StyleProfile(
        name="storytelling",
        description=(
            "Measured, warm and slightly slower delivery."
        ),
        speed_multiplier=0.96,
        volume_multiplier=1.0,
        bass_offset_db=0.8,
    ),
}


STYLE_PROFILES: Mapping[
    str,
    StyleProfile,
] = MappingProxyType(
    _STYLE_PROFILES
)


def clamp(
    value: float,
    minimum: float,
    maximum: float,
) -> float:
    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def resolve_style_controls(
    *,
    style: str,
    speed: float,
    volume: float,
    bass: float,
) -> ResolvedStyleControls:
    clean_style = (
        style
        .strip()
        .lower()
    )

    profile = STYLE_PROFILES.get(
        clean_style
    )

    if profile is None:
        allowed_styles = ", ".join(
            sorted(
                STYLE_PROFILES
            )
        )

        raise ValueError(
            "Style must be one of: "
            f"{allowed_styles}."
        )

    effective_speed = round(
        clamp(
            speed
            * profile.speed_multiplier,
            MIN_SPEED,
            MAX_SPEED,
        ),
        4,
    )

    effective_volume = round(
        clamp(
            volume
            * profile.volume_multiplier,
            MIN_VOLUME,
            MAX_VOLUME,
        ),
        4,
    )

    effective_bass = round(
        clamp(
            bass
            + profile.bass_offset_db,
            MIN_BASS_DB,
            MAX_BASS_DB,
        ),
        2,
    )

    return ResolvedStyleControls(
        style=clean_style,
        requested_speed=speed,
        requested_volume=volume,
        requested_bass=bass,
        effective_speed=effective_speed,
        effective_volume=effective_volume,
        effective_bass=effective_bass,
        profile=profile,
    )
