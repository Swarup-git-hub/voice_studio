from faster_whisper import WhisperModel


class AudioTranscriber:

    def __init__(self):

        self.model = WhisperModel(
            "base",
            device="cpu",
            compute_type="int8",
        )

    def transcribe(self, audio_path: str) -> str:

        segments, info = self.model.transcribe(
            audio_path,
            beam_size=5,
            language="en",          # Force English
            vad_filter=True,        # Remove silence
            condition_on_previous_text=False,
        )

        print("\n" + "=" * 60)
        print("WHISPER INFO")
        print("=" * 60)
        print("Detected Language :", info.language)
        print("Probability       :", info.language_probability)
        print("=" * 60)

        transcript_parts = []

        for segment in segments:

            print(
                f"[{segment.start:.2f}s -> {segment.end:.2f}s] "
                f"{segment.text}"
            )

            transcript_parts.append(segment.text.strip())

        transcript = " ".join(transcript_parts).strip()

        print("\nFinal Transcript:")
        print(transcript)
        print("=" * 60)

        return transcript


transcriber = AudioTranscriber()