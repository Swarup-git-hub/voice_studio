from __future__ import annotations

import io
import json
import time
import wave
from typing import Any
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.request import Request
from urllib.request import urlopen


BASE_URL = "http://127.0.0.1:8000"
INDICF5_URL = "http://127.0.0.1:8002"
VOICE_ID = 10

TELUGU_SENTENCE = (
    "ఈ వ్యవస్థ పొడవైన తెలుగు పాఠ్యాన్ని చిన్న భాగాలుగా "
    "విభజించి, ప్రతి భాగాన్ని వరుసగా స్వరంగా మార్చి, "
    "చివరలో అన్ని భాగాలను ఒకే స్పష్టమైన ఆడియోగా కలుపుతుంది."
)

TEST_TEXT = " ".join(
    TELUGU_SENTENCE
    for _ in range(18)
)


checks_passed = 0


def check(
    name: str,
    condition: bool,
    detail: str = "",
) -> None:
    global checks_passed

    if not condition:
        raise AssertionError(
            f"{name}: FAILED"
            + (
                f"\n{detail}"
                if detail
                else ""
            )
        )

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

            parsed = (
                json.loads(
                    raw_body.decode("utf-8")
                )
                if raw_body
                else None
            )

            return response.status, parsed

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
) -> bytes:
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
            if response.status != 200:
                raise RuntimeError(
                    "Audio download did not return HTTP 200."
                )

            return response.read()

    except HTTPError as error:
        error_body = error.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            f"Audio download failed with HTTP "
            f"{error.code}\n{error_body}"
        ) from error


print("=" * 88)
print(
    "MILESTONE 10.6.7B — LIVE LONG SEGMENTED "
    "INDICF5 REGRESSION"
)
print("=" * 88)

print("Input characters:", len(TEST_TEXT))

check(
    "Input exceeds one engine request",
    len(TEST_TEXT) > 1500,
    f"Characters={len(TEST_TEXT)}",
)

check(
    "Input remains within API limit",
    len(TEST_TEXT) <= 10_000,
    f"Characters={len(TEST_TEXT)}",
)

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

indic_status, indic_health = request_json(
    "GET",
    f"{INDICF5_URL}/health",
    timeout=30,
)

check(
    "IndicF5 service is healthy",
    indic_status == 200,
    repr(indic_health),
)

check(
    "IndicF5 model is loaded",
    bool(
        indic_health.get(
            "model_loaded",
            False,
        )
    ),
    repr(indic_health),
)

history_url = (
    f"{BASE_URL}/speech/history"
)

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
    "engine": "indicf5",
    "allow_fallback": False,
}

print()
print("Submitting long segmented request...")
print(
    "Characters:",
    len(TEST_TEXT),
)

started_at = time.perf_counter()

generation_status, generation = request_json(
    "POST",
    f"{BASE_URL}/speech/generate",
    body=payload,
    timeout=600,
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
    "IndicF5 was explicitly requested",
    generation[
        "engine_requested"
    ]
    == "indicf5",
)

check(
    "All segments used IndicF5",
    generation[
        "engine_used"
    ]
    == "indicf5",
    repr(
        generation[
            "engine_used"
        ]
    ),
)

check(
    "Fallback was not used",
    generation[
        "fallback_used"
    ]
    is False,
)

check(
    "Telugu was detected",
    generation[
        "detected_language"
    ]
    == "telugu",
    repr(
        generation[
            "detected_language"
        ]
    ),
)

routing_reason = str(
    generation[
        "routing_reason"
    ]
)

check(
    "Segmented phrase routing was used",
    routing_reason.startswith(
        "segmented_phrase_routing:"
    ),
    routing_reason,
)

check(
    "Response preserves long source text",
    len(
        generation["text"]
    )
    > 1500,
    (
        "Returned characters="
        f"{len(generation['text'])}"
    ),
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
    "Exactly one history row was created",
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
    "Long generation history is retrievable",
    len(
        matching_history
    )
    == 1,
)

history_item = matching_history[0]

check(
    "History stores IndicF5 metadata",
    history_item[
        "engine_used"
    ]
    == "indicf5",
)

audio_url = (
    f"{BASE_URL}"
    + generation[
        "audio_url"
    ]
)

audio_bytes = download_audio(
    audio_url,
    timeout=120,
)

check(
    "Joined audio is non-empty",
    len(audio_bytes) > 44,
    f"Bytes={len(audio_bytes)}",
)

with wave.open(
    io.BytesIO(
        audio_bytes
    ),
    "rb",
) as wav_file:
    metadata = {
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
    "Joined output is mono",
    metadata["channels"] == 1,
    repr(metadata),
)

check(
    "Joined output is PCM16",
    metadata["sample_width"] == 2,
    repr(metadata),
)

check(
    "Joined output is 24 kHz",
    metadata["sample_rate"] == 24_000,
    repr(metadata),
)

check(
    "Joined output contains audio frames",
    metadata["frames"] > 0,
    repr(metadata),
)

check(
    "Joined output has meaningful duration",
    metadata[
        "duration_seconds"
    ]
    > 10.0,
    repr(metadata),
)

print()
print("Generation ID:", generation_id)
print(
    "Output filename:",
    generation[
        "output_filename"
    ],
)
print("Routing reason:", routing_reason)
print("Audio URL:", audio_url)
print(
    "WAV metadata:",
    json.dumps(
        metadata,
        indent=2,
    ),
)

print()
print("=" * 88)
print(
    "MILESTONE 10.6.7B LIVE LONG SEGMENTED "
    "INDICF5 REGRESSION: PASSED"
)
print("=" * 88)
print("Checks passed:", checks_passed)
