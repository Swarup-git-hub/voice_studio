from pathlib import Path
import subprocess
import wave

import requests


class CosyVoiceEngine:

    def __init__(self):

        self.base_url = "http://127.0.0.1:8001"

    # ========================================================
    # Health check
    # ========================================================

    def load(self):

        try:

            response = requests.get(
                f"{self.base_url}/health",
                timeout=10,
            )

            response.raise_for_status()

            health_data = response.json()

            if not health_data.get(
                "model_loaded",
                True,
            ):

                raise RuntimeError(
                    "CosyVoice server is running, " "but the model is not loaded."
                )

            print("✓ Connected to CosyVoice Server")

        except Exception as error:

            raise RuntimeError(
                "CosyVoice Server is not ready.\n\n"
                "Start it using:\n"
                "python -m uvicorn server:app "
                "--host 127.0.0.1 --port 8001"
            ) from error

    # ========================================================
    # Generate speech
    # ========================================================

    def generate(
        self,
        reference_audio: str,
        prompt_text: str,
        text: str,
        output_path: str,
        speed: float = 1.0,
    ):

        reference_path = Path(reference_audio).resolve()

        destination_path = Path(output_path).resolve()

        clean_text = text.strip()
        clean_prompt_text = prompt_text.strip()

        if not reference_path.exists():

            raise FileNotFoundError(
                "CosyVoice reference audio " f"was not found:\n{reference_path}"
            )

        if not clean_text:

            raise ValueError("Synthesis text cannot be empty.")

        if not clean_prompt_text:

            raise ValueError("Prompt transcript cannot be empty.")

        if not 0.5 <= speed <= 2.0:

            raise ValueError("Speed must be between 0.5 and 2.0.")

        destination_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        print("\n" + "=" * 80)
        print("COSYVOICE ENGINE")
        print("=" * 80)

        print("Reference Audio:")
        print(reference_path)

        print("\nReference Exists:")
        print(reference_path.exists())

        print("\nText:")
        print(clean_text)

        print("\nSpeed:")
        print(speed)

        print("\nPrompt Text:")
        print(clean_prompt_text)

        payload = {
            "text": clean_text,
            "prompt_text": clean_prompt_text,
            "prompt_audio": str(reference_path),
            "speed": speed,
        }

        print("\nSending HTTP Request to CosyVoice...")

        try:

            response = requests.post(
                f"{self.base_url}/tts",
                json=payload,
                timeout=(10, 600),
            )

        except requests.ConnectionError as error:

            raise RuntimeError(
                "Could not connect to CosyVoice " "on http://127.0.0.1:8001."
            ) from error

        except requests.Timeout as error:

            raise RuntimeError("CosyVoice generation timed out.") from error

        except requests.RequestException as error:

            raise RuntimeError("CosyVoice request failed.") from error

        print("\nResponse Status:")
        print(response.status_code)

        if response.status_code != 200:

            print("\nResponse Body:")
            print(response.text)

            raise RuntimeError(
                "CosyVoice generation failed.\n"
                f"Status: {response.status_code}\n"
                f"Response: {response.text}"
            )

        if not response.content:

            raise RuntimeError("CosyVoice returned an empty response.")

        print("\nSaving Raw Generated Audio...")

        destination_path.write_bytes(response.content)

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
                "not be normalized as a WAV segment.\n"
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

            raise RuntimeError("The raw generated WAV was not saved.")

        if destination_path.stat().st_size <= 0:

            raise RuntimeError("The raw generated WAV is empty.")

        print("Raw Audio Saved Successfully")
        print("Path :", destination_path)
        print(
            "Size :",
            destination_path.stat().st_size,
            "bytes",
        )
        print("=" * 80)


engine = CosyVoiceEngine()