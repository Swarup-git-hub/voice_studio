from __future__ import annotations

import os
import sys
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from app.ai.segmenter import SegmentBoundary


@dataclass(
    frozen=True,
    slots=True,
)
class WavJoinInput:
    path: Path
    boundary_after: SegmentBoundary


class WavJoiner:
    """
    Join engine-generated WAV segments into one raw output WAV.

    Accepted input and output format:

    - 24,000 Hz
    - mono
    - signed PCM16
    - uncompressed WAV
    """

    SAMPLE_RATE = 24_000
    CHANNELS = 1
    SAMPLE_WIDTH = 2
    COMPRESSION_TYPE = "NONE"

    FADE_MILLISECONDS = 10

    PAUSE_MILLISECONDS = {
        "continuation": 60,
        "sentence": 180,
        "paragraph": 350,
        "none": 0,
    }

    @classmethod
    def _validate_boundary(
        cls,
        boundary: str,
    ) -> None:
        if boundary not in cls.PAUSE_MILLISECONDS:
            raise ValueError(
                "Unsupported WAV join boundary: "
                f"{boundary!r}."
            )

    @classmethod
    def _read_pcm16(
        cls,
        input_path: Path,
    ) -> array:
        resolved = input_path.expanduser().resolve()

        if not resolved.exists():
            raise FileNotFoundError(
                f"WAV segment was not found: {resolved}"
            )

        if not resolved.is_file():
            raise ValueError(
                f"WAV segment is not a file: {resolved}"
            )

        try:
            with wave.open(
                str(resolved),
                "rb",
            ) as wav_file:
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                sample_rate = wav_file.getframerate()
                compression_type = wav_file.getcomptype()
                frame_count = wav_file.getnframes()

                raw_frames = wav_file.readframes(
                    frame_count
                )

        except wave.Error as error:
            raise ValueError(
                f"Invalid WAV segment: {resolved}"
            ) from error

        if channels != cls.CHANNELS:
            raise ValueError(
                "Every WAV segment must be mono. "
                f"Received {channels} channels from {resolved.name}."
            )

        if sample_rate != cls.SAMPLE_RATE:
            raise ValueError(
                "Every WAV segment must use a 24000 Hz sample rate. "
                f"Received {sample_rate} Hz from {resolved.name}."
            )

        if sample_width != cls.SAMPLE_WIDTH:
            raise ValueError(
                "Every WAV segment must use PCM16 audio. "
                f"Received a {sample_width}-byte sample width "
                f"from {resolved.name}."
            )

        if compression_type != cls.COMPRESSION_TYPE:
            raise ValueError(
                "Every WAV segment must be uncompressed PCM audio."
            )

        samples = array(
            "h",
        )

        samples.frombytes(
            raw_frames
        )

        if sys.byteorder != "little":
            samples.byteswap()

        if not samples:
            raise ValueError(
                f"WAV segment contains no audio frames: {resolved}"
            )

        return samples

    @classmethod
    def _fade_edges(
        cls,
        samples: array,
    ) -> array:
        faded = array(
            "h",
            samples,
        )

        requested_fade_frames = round(
            cls.SAMPLE_RATE
            * cls.FADE_MILLISECONDS
            / 1000
        )

        fade_frames = min(
            requested_fade_frames,
            len(faded) // 2,
        )

        if fade_frames <= 1:
            return faded

        denominator = fade_frames - 1

        for index in range(
            fade_frames
        ):
            fade_in_factor = (
                index / denominator
            )

            fade_out_factor = (
                (
                    fade_frames
                    - 1
                    - index
                )
                / denominator
            )

            faded[index] = int(
                round(
                    faded[index]
                    * fade_in_factor
                )
            )

            tail_index = (
                len(faded)
                - fade_frames
                + index
            )

            faded[tail_index] = int(
                round(
                    faded[tail_index]
                    * fade_out_factor
                )
            )

        return faded

    @classmethod
    def _silence(
        cls,
        milliseconds: int,
    ) -> array:
        frame_count = round(
            cls.SAMPLE_RATE
            * milliseconds
            / 1000
        )

        return array(
            "h",
            [0],
        ) * frame_count

    @classmethod
    def _write_output(
        cls,
        output_path: Path,
        samples: array,
    ) -> None:
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_samples = array(
            "h",
            samples,
        )

        if sys.byteorder != "little":
            output_samples.byteswap()

        with wave.open(
            str(output_path),
            "wb",
        ) as wav_file:
            wav_file.setnchannels(
                cls.CHANNELS
            )

            wav_file.setsampwidth(
                cls.SAMPLE_WIDTH
            )

            wav_file.setframerate(
                cls.SAMPLE_RATE
            )

            wav_file.setcomptype(
                cls.COMPRESSION_TYPE,
                "not compressed",
            )

            wav_file.writeframes(
                output_samples.tobytes()
            )

    @classmethod
    def _validate_output(
        cls,
        output_path: Path,
        expected_frames: int,
    ) -> None:
        if not output_path.exists():
            raise RuntimeError(
                "Joined WAV was not created."
            )

        if output_path.stat().st_size <= 44:
            raise RuntimeError(
                "Joined WAV is empty."
            )

        with wave.open(
            str(output_path),
            "rb",
        ) as wav_file:
            if wav_file.getnchannels() != cls.CHANNELS:
                raise RuntimeError(
                    "Joined WAV is not mono."
                )

            if wav_file.getframerate() != cls.SAMPLE_RATE:
                raise RuntimeError(
                    "Joined WAV is not 24000 Hz."
                )

            if wav_file.getsampwidth() != cls.SAMPLE_WIDTH:
                raise RuntimeError(
                    "Joined WAV is not PCM16."
                )

            actual_frames = wav_file.getnframes()

        if actual_frames != expected_frames:
            raise RuntimeError(
                "Joined WAV frame count mismatch. "
                f"Expected {expected_frames}, "
                f"received {actual_frames}."
            )

    @classmethod
    def join(
        cls,
        inputs: Sequence[WavJoinInput],
        output_path: str | Path,
    ) -> dict[str, object]:
        if not inputs:
            raise ValueError(
                "At least one WAV segment is required."
            )

        resolved_output = Path(
            output_path
        ).expanduser().resolve()

        resolved_inputs = [
            WavJoinInput(
                path=item.path.expanduser().resolve(),
                boundary_after=item.boundary_after,
            )
            for item in inputs
        ]

        for item in resolved_inputs:
            cls._validate_boundary(
                item.boundary_after
            )

            if item.path == resolved_output:
                raise ValueError(
                    "The joined output path cannot be one "
                    "of the source WAV paths."
                )

        if (
            resolved_inputs[-1].boundary_after
            != "none"
        ):
            raise ValueError(
                "The final WAV segment must use the "
                "'none' boundary."
            )

        temporary_output = (
            resolved_output.with_name(
                resolved_output.name
                + ".join_tmp.wav"
            )
        )

        temporary_output.unlink(
            missing_ok=True
        )

        combined = array(
            "h",
        )

        pause_values: list[int] = []

        try:
            for item in resolved_inputs:
                samples = cls._read_pcm16(
                    item.path
                )

                faded_samples = (
                    cls._fade_edges(
                        samples
                    )
                )

                combined.extend(
                    faded_samples
                )

                pause_ms = (
                    cls.PAUSE_MILLISECONDS[
                        item.boundary_after
                    ]
                )

                pause_values.append(
                    pause_ms
                )

                if pause_ms > 0:
                    combined.extend(
                        cls._silence(
                            pause_ms
                        )
                    )

            if not combined:
                raise RuntimeError(
                    "WAV joining produced no audio frames."
                )

            cls._write_output(
                temporary_output,
                combined,
            )

            cls._validate_output(
                temporary_output,
                len(combined),
            )

            resolved_output.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            os.replace(
                temporary_output,
                resolved_output,
            )

            cls._validate_output(
                resolved_output,
                len(combined),
            )

        except Exception:
            temporary_output.unlink(
                missing_ok=True
            )

            raise

        return {
            "output_path": str(
                resolved_output
            ),
            "segment_count": len(
                resolved_inputs
            ),
            "sample_rate": cls.SAMPLE_RATE,
            "channels": cls.CHANNELS,
            "sample_width": cls.SAMPLE_WIDTH,
            "fade_milliseconds": (
                cls.FADE_MILLISECONDS
            ),
            "pause_milliseconds": (
                pause_values
            ),
            "total_frames": len(
                combined
            ),
            "duration_seconds": (
                len(combined)
                / cls.SAMPLE_RATE
            ),
        }


wav_joiner = WavJoiner()
