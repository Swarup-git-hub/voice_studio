from dataclasses import dataclass
from pathlib import Path
import os
import re
import subprocess
import uuid

MIN_REFERENCE_SECONDS = 8.0
TARGET_REFERENCE_SECONDS = 12.0
MAX_REFERENCE_SECONDS = 15.0

SILENCE_THRESHOLD_DB = -42
SILENCE_MIN_SECONDS = 0.25

EDGE_PADDING_SECONDS = 0.05


@dataclass(frozen=True)
class ReferencePreparationResult:
    path: Path
    source_start: float
    source_end: float
    duration: float


def _run_command(
    command: list[str],
    error_message: str,
) -> subprocess.CompletedProcess[str]:

    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )

    except subprocess.CalledProcessError as error:
        details = error.stderr.strip() if error.stderr else str(error)

        raise RuntimeError(f"{error_message}\n{details}") from error


def get_audio_duration(
    audio_path: Path,
) -> float:

    result = _run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        "Could not read the audio duration.",
    )

    try:
        duration = float(result.stdout.strip())

    except ValueError as error:
        raise RuntimeError("FFprobe returned an invalid duration.") from error

    if duration <= 0:
        raise ValueError("The reference audio has no usable duration.")

    return duration


def detect_silence_intervals(
    audio_path: Path,
    audio_duration: float,
) -> list[tuple[float, float]]:

    command = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        str(audio_path),
        "-af",
        (
            "silencedetect="
            f"noise={SILENCE_THRESHOLD_DB}dB:"
            f"d={SILENCE_MIN_SECONDS}"
        ),
        "-f",
        "null",
        os.devnull,
    ]

    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "FFmpeg could not analyze silence regions.\n" + result.stderr.strip()
        )

    silence_intervals: list[tuple[float, float]] = []

    pending_start: float | None = None

    start_pattern = re.compile(r"silence_start:\s*([0-9.]+)")

    end_pattern = re.compile(r"silence_end:\s*([0-9.]+)")

    for line in result.stderr.splitlines():

        start_match = start_pattern.search(line)

        if start_match:
            pending_start = float(start_match.group(1))

        end_match = end_pattern.search(line)

        if not end_match:
            continue

        silence_end = float(end_match.group(1))

        silence_start = pending_start if pending_start is not None else 0.0

        if silence_end > silence_start:
            silence_intervals.append(
                (
                    max(0.0, silence_start),
                    min(
                        audio_duration,
                        silence_end,
                    ),
                )
            )

        pending_start = None

    if pending_start is not None and pending_start < audio_duration:
        silence_intervals.append(
            (
                pending_start,
                audio_duration,
            )
        )

    return silence_intervals


def choose_reference_segment(
    audio_duration: float,
    silence_intervals: list[tuple[float, float]],
) -> tuple[float, float]:

    leading_silence_end = 0.0

    for silence_start, silence_end in silence_intervals:
        if silence_start <= 0.10:
            leading_silence_end = max(
                leading_silence_end,
                silence_end,
            )

    segment_start = max(
        0.0,
        leading_silence_end - EDGE_PADDING_SECONDS,
    )

    usable_audio_end = audio_duration

    for silence_start, silence_end in silence_intervals:
        if silence_end >= audio_duration - 0.10:
            usable_audio_end = min(
                usable_audio_end,
                silence_start,
            )

    minimum_end = segment_start + MIN_REFERENCE_SECONDS

    maximum_end = min(
        segment_start + MAX_REFERENCE_SECONDS,
        usable_audio_end,
    )

    if maximum_end < minimum_end:
        available_seconds = max(
            0.0,
            usable_audio_end - segment_start,
        )

        raise ValueError(
            "The recording does not contain enough "
            "continuous speech for a synchronized "
            "reference. At least "
            f"{MIN_REFERENCE_SECONDS:.0f} seconds of "
            "usable speech is required. Found about "
            f"{available_seconds:.1f} seconds."
        )

    target_end = min(
        segment_start + TARGET_REFERENCE_SECONDS,
        maximum_end,
    )

    phrase_boundaries = [
        silence_start
        for silence_start, _ in silence_intervals
        if minimum_end <= silence_start <= maximum_end
    ]

    if phrase_boundaries:
        segment_end = min(
            phrase_boundaries,
            key=lambda boundary: (
                abs(boundary - target_end),
                -boundary,
            ),
        )

    else:
        segment_end = target_end

    segment_end = min(
        maximum_end,
        segment_end + EDGE_PADDING_SECONDS,
    )

    if segment_end - segment_start < MIN_REFERENCE_SECONDS:
        segment_end = minimum_end

    return segment_start, segment_end


def extract_reference_segment(
    input_path: Path,
    output_path: Path,
    segment_start: float,
    segment_end: float,
) -> None:

    segment_duration = segment_end - segment_start

    _run_command(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(input_path),
            "-ss",
            f"{segment_start:.3f}",
            "-t",
            f"{segment_duration:.3f}",
            "-vn",
            "-ar",
            "24000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ],
        ("Could not extract the synchronized " "reference segment."),
    )

    if not output_path.exists():
        raise RuntimeError(
            "FFmpeg completed but the synchronized " "reference file was not created."
        )

    if output_path.stat().st_size <= 0:
        output_path.unlink(missing_ok=True)

        raise RuntimeError("The synchronized reference file is empty.")


def prepare_reference_audio(
    converted_audio_path: str | Path,
) -> ReferencePreparationResult:

    input_path = Path(converted_audio_path).resolve()

    if not input_path.exists():
        raise FileNotFoundError(
            "Converted reference audio was not found:\n" f"{input_path}"
        )

    source_duration = get_audio_duration(input_path)

    silence_intervals = detect_silence_intervals(
        audio_path=input_path,
        audio_duration=source_duration,
    )

    segment_start, segment_end = choose_reference_segment(
        audio_duration=source_duration,
        silence_intervals=silence_intervals,
    )

    output_path = input_path.with_name("reference_" + uuid.uuid4().hex + ".wav")

    extract_reference_segment(
        input_path=input_path,
        output_path=output_path,
        segment_start=segment_start,
        segment_end=segment_end,
    )

    prepared_duration = get_audio_duration(output_path)

    if prepared_duration < (MIN_REFERENCE_SECONDS - 0.10):
        output_path.unlink(missing_ok=True)

        raise ValueError(
            "The prepared reference is shorter " "than the minimum supported duration."
        )

    if prepared_duration > (MAX_REFERENCE_SECONDS + 0.20):
        output_path.unlink(missing_ok=True)

        raise ValueError(
            "The prepared reference is longer " "than the configured maximum duration."
        )

    return ReferencePreparationResult(
        path=output_path.resolve(),
        source_start=segment_start,
        source_end=segment_end,
        duration=prepared_duration,
    )