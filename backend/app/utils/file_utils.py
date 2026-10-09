from pathlib import Path
import uuid


def generate_unique_filename(filename: str):

    extension = Path(filename).suffix.lower()

    unique_name = f"{uuid.uuid4()}{extension}"

    return unique_name