import wave
from pathlib import Path


class AudioAnalyzer:

    def __init__(self, audio_path: str):

        self.audio_path = Path(audio_path)

    def analyze(self):

        with wave.open(str(self.audio_path), "rb") as wav:

            channels = wav.getnchannels()

            sample_rate = wav.getframerate()

            frames = wav.getnframes()

            duration = frames / float(sample_rate)

            sample_width = wav.getsampwidth()

        return {
            "duration": round(duration, 2),
            "sample_rate": sample_rate,
            "channels": channels,
            "sample_width": sample_width,
        }

    def validate(self):

        info = self.analyze()

        errors = []

        if info["duration"] < 10:

            errors.append("Audio must be at least 10 seconds.")

        if info["duration"] > 300:

            errors.append("Audio must be less than 5 minutes.")

        if info["sample_rate"] < 16000:

            errors.append("Sample rate must be at least 16kHz.")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "info": info,
        }
