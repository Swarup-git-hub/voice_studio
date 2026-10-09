from __future__ import annotations

from pathlib import Path


backend_root = Path(__file__).resolve().parents[1]

target_path = (
    backend_root
    / "app"
    / "services"
    / "cosyvoice_engine.py"
)

source = target_path.read_text(
    encoding="utf-8"
)

old_import = """from pathlib import Path

import requests
"""

new_import = """from pathlib import Path
import subprocess
import wave

import requests
"""

if new_import not in source:
    if source.count(old_import) != 1:
        raise RuntimeError(
            "Could not find exactly one CosyVoice import marker."
        )

    source = source.replace(
        old_import,
        new_import,
        1,
    )

old_write = """        destination_path.write_bytes(response.content)

        if not destination_path.exists():
"""

new_write = """        destination_path.write_bytes(response.content)

        normalized_path = destination_path.with_name(
            destination_path.stem
            + "_normalized.wav"
        )

        normalization_command = [
            "ffmpeg",
            "-y",
            "-nostdin",
            "-loglevel",
            "error",
            "-i",
            str(destination_path),
            "-ar",
            "24000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(normalized_path),
        ]

        try:
            subprocess.run(
                normalization_command,
                check=True,
                capture_output=True,
                text=True,
            )

            normalized_path.replace(
                destination_path
            )

        except subprocess.CalledProcessError as error:
            normalized_path.unlink(
                missing_ok=True
            )

            destination_path.unlink(
                missing_ok=True
            )

            ffmpeg_error = (
                error.stderr.strip()
                if error.stderr
                else "Unknown FFmpeg error."
            )

            raise RuntimeError(
                "CosyVoice returned audio that could "
                "not be normalized as a WAV segment.\\n"
                f"FFmpeg error: {ffmpeg_error}"
            ) from error

        finally:
            normalized_path.unlink(
                missing_ok=True
            )

        try:
            with wave.open(
                str(destination_path),
                "rb",
            ) as wav_file:
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                sample_rate = wav_file.getframerate()
                frame_count = wav_file.getnframes()

        except (wave.Error, EOFError) as error:
            destination_path.unlink(
                missing_ok=True
            )

            raise RuntimeError(
                "Normalized CosyVoice output is not "
                "a readable PCM WAV file."
            ) from error

        if (
            channels != 1
            or sample_width != 2
            or sample_rate != 24000
            or frame_count <= 0
        ):
            destination_path.unlink(
                missing_ok=True
            )

            raise RuntimeError(
                "Normalized CosyVoice output must be "
                "24 kHz mono PCM16 with audio frames."
            )

        if not destination_path.exists():
"""

if new_write not in source:
    if source.count(old_write) != 1:
        raise RuntimeError(
            "Could not find exactly one CosyVoice "
            "response-write marker."
        )

    source = source.replace(
        old_write,
        new_write,
        1,
    )

required_markers = [
    "normalization_command = [",
    '"pcm_s16le"',
    "with wave.open(",
    "sample_rate != 24000",
]

for marker in required_markers:
    if marker not in source:
        raise RuntimeError(
            f"Required marker is missing after patch: {marker}"
        )

target_path.write_text(
    source,
    encoding="utf-8",
)

print(
    "Milestone 10.6.7C CosyVoice WAV "
    "normalization: APPLIED"
)
