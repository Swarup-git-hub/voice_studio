from pathlib import Path

from app.ai.loader import loader
from app.ai.preprocess import TextPreprocessor


class AIEngine:

    def __init__(self):

        self.model = loader.load()

    def generate(
        self,
        reference_audio: str,
        text: str,
        output_path: str,
        speed: float = 1.0,
    ):

        TextPreprocessor.validate(text)

        text = TextPreprocessor.clean(text)

        reference_audio = Path(reference_audio)

        if not reference_audio.exists():

            raise FileNotFoundError(reference_audio)

        print("=" * 60)
        print("AI ENGINE")
        print("=" * 60)

        print("Reference :", reference_audio.name)

        print("Characters:", len(text))

        print("Speed :", speed)

        print("Output :", output_path)

        return output_path


engine = AIEngine()
