from __future__ import annotations

import io
import json
import sys
import time
import wave
from typing import Any
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.request import Request
from urllib.request import urlopen


BASE_URL = "http://127.0.0.1:8000"
INDICF5_URL = "http://127.0.0.1:8002"

VOICE_ID = 10

TEST_TEXT = (
    "నమస్కారం. ఇది తెలుగు స్వర నిర్మాణం, "
    "స్పష్టత మరియు సహజమైన ఉచ్చారణను పరీక్షించే "
    "ప్రత్యక్ష పరీక్ష."
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

            parsed_body = (
                json.loads(
                    raw_body.decode("utf-8")
                )
                if raw_body
                else None
            )

            return (
                response.status,
                parsed_body,
            )

    except HTTPError as error:
        raw_error = error.read()

        error_text = raw_error.decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            f"HTTP {error.code} from {url}\n"
            f"{error_text}"
        ) from error

    except URLError as error:
        raise RuntimeError(
            f"Could not connect to {url}: {error}"
        ) from error


def download_bytes(
    url: str,
    timeout: int = 60,
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
        body = error.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            f"Audio request failed with HTTP "
            f"{error.code}:\n{body}"
        ) from error


def discover_generation_path(
    openapi_document: dict[str, Any],
) -> str:
    paths = openapi_document.get(
        "paths",
        {},
    )

    preferred_path = (
        "/speech/generate"
    )

    if (
        preferred_path in paths
        and "post" in paths[preferred_path]
    ):
        return preferred_path

    candidates: list[str] = []

    for path, operations in paths.items():
        if not path.startswith(
            "/speech"
        ):
            continue

        post_operation = operations.get(
            "post"
        )

        if not isinstance(
            post_operation,
            dict,
        ):
            continue

        operation_text = json.dumps(
            post_operation,
        )

        if (
            "GenerateSpeechRequest"
            in operation_text
            or "GenerateSpeechResponse"
            in operation_text
        ):
            candidates.append(
                path
            )

    if len(candidates) != 1:
        raise RuntimeError(
            "Could not identify exactly one speech "
            f"generation endpoint. Candidates={candidates}"
        )

    return candidates[0]


print("=" * 88)
print("MILESTONE 10.6.7A — LIVE INDICF5 TELUGU REGRESSION")
print("=" * 88)

backend_status, backend_health = (
    request_json(
        "GET",
        f"{BASE_URL}/health",
        timeout=15,
    )
)

check(
    "Main backend is healthy",
    backend_status == 200,
    repr(backend_health),
)

indic_status, indic_health = (
    request_json(
        "GET",
        f"{INDICF5_URL}/health",
        timeout=30,
    )
)

check(
    "IndicF5 service is healthy",
    indic_status == 200,
    repr(indic_health),
)

model_loaded = bool(
    indic_health.get(
        "model_loaded",
        False,
    )
)

check(
    "IndicF5 model is loaded",
    model_loaded,
    repr(indic_health),
)

openapi_status, openapi_document = (
    request_json(
        "GET",
        f"{BASE_URL}/openapi.json",
        timeout=15,
    )
)

check(
    "Backend OpenAPI is available",
    openapi_status == 200,
)

generation_path = (
    discover_generation_path(
        openapi_document
    )
)

print(
    "Generation endpoint:",
    generation_path,
)

history_url = (
    f"{BASE_URL}/speech/history"
)

before_status, history_before = (
    request_json(
        "GET",
        history_url,
        timeout=15,
    )
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
    "engine": "indicf5",
    "allow_fallback": False,
}

print()
print("Submitting real IndicF5 request...")
print(
    json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )
)

started_at = time.perf_counter()

generation_status, generation = (
    request_json(
        "POST",
        urljoin(
            BASE_URL,
            generation_path,
        ),
        body=payload,
        timeout=300,
    )
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
    f"Missing={sorted(missing_fields)}",
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
    repr(
        generation[
            "engine_requested"
        ]
    ),
)

check(
    "IndicF5 generated the audio",
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

after_status, history_after = (
    request_json(
        "GET",
        history_url,
        timeout=15,
    )
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
        f"Expected={{"
        f"{generation_id}"
        f"}}; Actual={new_ids}"
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

history_item = (
    matching_history[0]
)

check(
    "History stores IndicF5 engine metadata",
    history_item[
        "engine_used"
    ]
    == "indicf5",
    repr(
        history_item[
            "engine_used"
        ]
    ),
)

audio_url = urljoin(
    BASE_URL,
    generation[
        "audio_url"
    ],
)

audio_status, content_type, audio_bytes = (
    download_bytes(
        audio_url,
        timeout=60,
    )
)

check(
    "Generated audio is downloadable",
    audio_status == 200,
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
    wav_metadata[
        "channels"
    ]
    == 1,
    repr(wav_metadata),
)

check(
    "Output is PCM16",
    wav_metadata[
        "sample_width"
    ]
    == 2,
    repr(wav_metadata),
)

check(
    "Output is 24 kHz",
    wav_metadata[
        "sample_rate"
    ]
    == 24_000,
    repr(wav_metadata),
)

check(
    "Output contains audio frames",
    wav_metadata[
        "frames"
    ]
    > 0,
    repr(wav_metadata),
)

print()
print("Generation ID:", generation_id)
print(
    "Output filename:",
    generation[
        "output_filename"
    ],
)
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
    "MILESTONE 10.6.7A LIVE INDICF5 "
    "TELUGU REGRESSION: PASSED"
)
print("=" * 88)
print("Checks passed:", checks_passed)
