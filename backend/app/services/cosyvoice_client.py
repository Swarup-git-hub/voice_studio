import requests


COSYVOICE_URL = "http://127.0.0.1:8001/tts"


def generate_speech(
    text: str,
    prompt_text: str,
    prompt_audio: str,
):
    payload = {
        "text": text,
        "prompt_text": prompt_text,
        "prompt_audio": prompt_audio,
    }

    response = requests.post(
        COSYVOICE_URL,
        json=payload,
    )

    response.raise_for_status()

    return response.content