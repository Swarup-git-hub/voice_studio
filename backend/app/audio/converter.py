import subprocess
from pathlib import Path
import os


def convert_to_wav(input_file: str) -> str:
    """
    Convert any supported audio to:
    - WAV
    - 24kHz
    - Mono
    - Maximum 25 seconds
    """

    input_path = Path(input_file)

    # If input is already WAV, create a temporary output
    if input_path.suffix.lower() == ".wav":
        output_path = input_path.with_name(
            input_path.stem + "_converted.wav"
        )
    else:
        output_path = input_path.with_suffix(".wav")

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),

        "-ar",
        "24000",

        "-ac",
        "1",

        "-t",
        "25",

        str(output_path)
    ]

    subprocess.run(
        command,
        check=True,
    )

    # Replace original WAV safely
    if input_path.suffix.lower() == ".wav":

        os.remove(input_path)

        output_path.rename(input_path)

        return str(input_path)

    return str(output_path)