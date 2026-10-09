from __future__ import annotations

import io
import json
import time
import wave
from typing import Any
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.request import Request
from urllib.request import urlopen


BASE_URL = "http://127.0.0.1:8000"
COSYVOICE_URL = "http://127.0.0.1:8001"
VOICE_ID = 10

TEST_TEXT = (
    "Hello everyone. This is a real English voice generation test. "
    "The system should produce clear, natural speech using CosyVoice."
)

checks_passed = 0


def check(
    name: str,
    condition: bool,
    detail: str = "",
) -> None:
    global checks_passed

    if not condition:
        message = f"{name}: FAILED"

        if detail:
            message += f"\n{detail}"

        raise AssertionError(message)

    checks_passed += 1
    print(f"{name}: PASSED")


def request_json(
    method: str,
    url: str,
    body: dict[str, Any] | None = None,
    timeout: int = 30,
) -> tuple[int, Any]:
    data = None

    headers = {
        "Accept": "application/json",
    }

    if body is not None:
        data = json.dumps(
            body,
            ensure_ascii=False,
        ).encode("utf-8")

        headers["Content-Type"] = (
            "application/json; charset=utf-8"
        )

    request = Request(
        url=url,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urlopen(
            request,
            timeout=timeout,
        ) as response:
            raw_body = response.read()

            parsed_body = (
                json.loads(
                    raw_body.decode("utf-8")
                )
                if raw_body
                else None
            )

            return response.status, parsed_body

    except HTTPError as error:
        error_body = error.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            f"HTTP {error.code} from {url}\n"
            f"{error_body}"
        ) from error

    except URLError as error:
        raise RuntimeError(
            f"Could not connect to {url}: {error}"
        ) from error


def download_audio(
    url: str,
    timeout: int = 120,
) -> tuple[int, str, bytes]:
    request = Request(
        url=url,
        headers={
            "Accept": "audio/wav",
        },
        method="GET",
    )

    try:
        with urlopen(
            request,
            timeout=timeout,
        ) as response:
            return (
                response.status,
                response.headers.get(
                    "Content-Type",
                    "",
                ),
                response.read(),
            )

    except HTTPError as error:
        error_body = error.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            f"Audio request failed with HTTP "
            f"{error.code}\n{error_body}"
        ) from error


print("=" * 88)
print("MILESTONE 10.6.7C — LIVE COSYVOICE ENGLISH REGRESSION")
print("=" * 88)

backend_status, backend_health = request_json(
    "GET",
    f"{BASE_URL}/health",
    timeout=15,
)

check(
    "Main backend is healthy",
    backend_status == 200,
    repr(backend_health),
)

cosy_status, cosy_health = request_json(
    "GET",
    f"{COSYVOICE_URL}/health",
    timeout=30,
)

check(
    "CosyVoice service is healthy",
    cosy_status == 200,
    repr(cosy_health),
)

check(
    "CosyVoice model is loaded",
    bool(
        cosy_health.get(
            "model_loaded",
            False,
        )
    ),
    repr(cosy_health),
)

history_url = f"{BASE_URL}/speech/history"

before_status, history_before = request_json(
    "GET",
    history_url,
    timeout=15,
)

check(
    "History is readable before generation",
    (
        before_status == 200
        and isinstance(
            history_before,
            list,
        )
    ),
    repr(history_before),
)

before_ids = {
    int(item["id"])
    for item in history_before
}

payload = {
    "voice_id": VOICE_ID,
    "text": TEST_TEXT,
    "speed": 1.0,
    "volume": 1.0,
    "bass": 0.0,
    "engine": "cosyvoice",
    "allow_fallback": False,
}

print()
print("Submitting real CosyVoice request...")

print(
    json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )
)

started_at = time.perf_counter()

generation_status, generation = request_json(
    "POST",
    f"{BASE_URL}/speech/generate",
    body=payload,
    timeout=300,
)

elapsed_seconds = (
    time.perf_counter()
    - started_at
)

print()
print(
    "Generation elapsed seconds:",
    round(
        elapsed_seconds,
        2,
    ),
)

print(
    json.dumps(
        generation,
        ensure_ascii=False,
        indent=2,
        default=str,
    )
)

check(
    "Generation returned HTTP 200",
    generation_status == 200,
)

required_fields = {
    "id",
    "voice_id",
    "text",
    "output_filename",
    "engine_requested",
    "engine_used",
    "detected_language",
    "fallback_used",
    "routing_reason",
    "audio_url",
    "download_url",
}

missing_fields = (
    required_fields
    - set(
        generation.keys()
    )
)

check(
    "Generation response contains routing metadata",
    not missing_fields,
    f"Missing fields={sorted(missing_fields)}",
)

generation_id = int(
    generation["id"]
)

check(
    "Correct voice was used",
    int(
        generation["voice_id"]
    )
    == VOICE_ID,
)

check(
    "CosyVoice was explicitly requested",
    generation["engine_requested"]
    == "cosyvoice",
    repr(
        generation["engine_requested"]
    ),
)

check(
    "CosyVoice generated the audio",
    generation["engine_used"]
    == "cosyvoice",
    repr(
        generation["engine_used"]
    ),
)

check(
    "Fallback was not used",
    generation["fallback_used"]
    is False,
)

check(
    "English was detected",
    generation["detected_language"]
    == "english",
    repr(
        generation["detected_language"]
    ),
)

routing_reason = str(
    generation["routing_reason"]
)

check(
    "Explicit CosyVoice routing was recorded",
    "explicit_cosyvoice"
    in routing_reason,
    routing_reason,
)

after_status, history_after = request_json(
    "GET",
    history_url,
    timeout=15,
)

check(
    "History is readable after generation",
    (
        after_status == 200
        and isinstance(
            history_after,
            list,
        )
    ),
)

after_ids = {
    int(item["id"])
    for item in history_after
}

new_ids = (
    after_ids
    - before_ids
)

check(
    "Exactly one history record was created",
    new_ids == {
        generation_id
    },
    (
        f"Expected={{{generation_id}}}; "
        f"Actual={new_ids}"
    ),
)

matching_history = [
    item
    for item in history_after
    if int(item["id"])
    == generation_id
]

check(
    "Generated history record is retrievable",
    len(
        matching_history
    )
    == 1,
)

history_item = matching_history[0]

check(
    "History stores CosyVoice metadata",
    history_item["engine_used"]
    == "cosyvoice",
    repr(
        history_item["engine_used"]
    ),
)

audio_url = urljoin(
    BASE_URL,
    generation["audio_url"],
)

audio_status, content_type, audio_bytes = download_audio(
    audio_url,
    timeout=120,
)

check(
    "Generated audio is downloadable",
    audio_status == 200,
)

check(
    "Generated audio content type is valid",
    (
        "audio" in content_type.lower()
        or "wav" in content_type.lower()
        or "octet-stream" in content_type.lower()
    ),
    content_type,
)

check(
    "Generated audio is non-empty",
    len(audio_bytes) > 44,
    f"Bytes={len(audio_bytes)}",
)

with wave.open(
    io.BytesIO(
        audio_bytes
    ),
    "rb",
) as wav_file:
    wav_metadata = {
        "channels": (
            wav_file.getnchannels()
        ),
        "sample_width": (
            wav_file.getsampwidth()
        ),
        "sample_rate": (
            wav_file.getframerate()
        ),
        "frames": (
            wav_file.getnframes()
        ),
        "duration_seconds": (
            wav_file.getnframes()
            / wav_file.getframerate()
        ),
    }

check(
    "Output is mono",
    wav_metadata["channels"] == 1,
    repr(wav_metadata),
)

check(
    "Output is PCM16",
    wav_metadata["sample_width"] == 2,
    repr(wav_metadata),
)

check(
    "Output is 24 kHz",
    wav_metadata["sample_rate"] == 24_000,
    repr(wav_metadata),
)

check(
    "Output contains audio frames",
    wav_metadata["frames"] > 0,
    repr(wav_metadata),
)

check(
    "Output has meaningful duration",
    wav_metadata["duration_seconds"] > 1.0,
    repr(wav_metadata),
)

print()
print("Generation ID:", generation_id)
print(
    "Output filename:",
    generation["output_filename"],
)
print("Routing reason:", routing_reason)
print("Audio URL:", audio_url)

print(
    "WAV metadata:",
    json.dumps(
        wav_metadata,
        indent=2,
    ),
)

print()
print("=" * 88)
print(
    "MILESTONE 10.6.7C LIVE COSYVOICE "
    "ENGLISH REGRESSION: PASSED"
)
print("=" * 88)
print("Checks passed:", checks_passed)
