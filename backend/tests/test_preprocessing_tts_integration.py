from __future__ import annotations

import shutil
import uuid
import wave
from pathlib import Path
from typing import Any

from app.ai.preprocess import TextPreprocessor
from app.core.config import settings
from app.services.engine_router import engine_router
from app.services.tts_service import TTSService


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
            + (f"\n{detail}" if detail else "")
        )

    checks_passed += 1
    print(f"{name}: PASSED")


def write_test_wav(
    path: Path,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with wave.open(
        str(path),
        "wb",
    ) as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(24000)
        wav_file.writeframes(
            b"\x00\x00" * 2400
        )


class FakeVoice:
    def __init__(
        self,
        wav_filename: str,
    ) -> None:
        self.id = 905
        self.voice_name = "Preprocessing Contract Voice"
        self.wav_filename = wav_filename
        self.transcript = (
            '  “Hello”\u200b   API.  '
        )


class FakeQuery:
    def __init__(
        self,
        voice: FakeVoice,
    ) -> None:
        self.voice = voice

    def filter(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> "FakeQuery":
        return self

    def first(
        self,
    ) -> FakeVoice:
        return self.voice


class FakeDatabase:
    def __init__(
        self,
        voice: FakeVoice,
    ) -> None:
        self.voice = voice
        self.query_called = False
        self.added = None
        self.committed = False
        self.rolled_back = False

    def query(
        self,
        _model: Any,
    ) -> FakeQuery:
        self.query_called = True
        return FakeQuery(
            self.voice
        )

    def add(
        self,
        item: Any,
    ) -> None:
        self.added = item

    def flush(
        self,
    ) -> None:
        if self.added is None:
            raise AssertionError(
                "Nothing was added before flush."
            )

        self.added.id = 9050

    def commit(
        self,
    ) -> None:
        self.committed = True

    def rollback(
        self,
    ) -> None:
        self.rolled_back = True


print("=" * 80)
print("MILESTONE 10.5 PREPROCESSING–TTS INTEGRATION")
print("=" * 80)

service = TTSService()

voices_folder = Path(
    settings.VOICE_FOLDER
).resolve()

reference_filename = (
    "milestone10_5_reference_"
    + uuid.uuid4().hex
    + ".wav"
)

reference_path = (
    voices_folder
    / reference_filename
)

final_output_path: Path | None = None

original_router_generate = (
    engine_router.generate
)

original_apply_controls = (
    service.apply_audio_controls
)

captured_router_arguments: dict[str, Any] = {}

try:
    write_test_wav(
        reference_path
    )

    fake_voice = FakeVoice(
        reference_filename
    )

    fake_database = FakeDatabase(
        fake_voice
    )

    source_input = (
        '  “Browser”లో   URL   API!!!!  '
    )

    expected_history_text = (
        '"Browser"లో URL API!'
    )

    expected_synthesis_text = (
        '"Browser"లో U R L A P I!'
    )

    expected_prompt_text = (
        '"Hello" API.'
    )

    def fake_router_generate(
        **kwargs: Any,
    ) -> dict[str, Any]:
        captured_router_arguments.update(
            kwargs
        )

        output_path = Path(
            kwargs["output_path"]
        ).resolve()

        write_test_wav(
            output_path
        )

        detected_language = (
            engine_router.detect_language(
                kwargs["detection_text"]
            )
        )

        return {
            "engine": "indicf5",
            "engine_requested": "indicf5",
            "engine_used": "indicf5",
            "detected_language": detected_language,
            "fallback_used": False,
            "routing_reason": "explicit_indicf5",
            "quality_warning": None,
            "failed_attempts": [],
            "speed_requested": kwargs["speed"],
            "speed_applied_by_engine": False,
        }

    def fake_apply_controls(
        *,
        raw_audio: Path,
        final_audio: Path,
        volume: float,
        bass: float,
        speed: float = 1.0,
        apply_speed: bool = False,
    ) -> None:
        del volume
        del bass
        del speed
        del apply_speed

        shutil.move(
            str(raw_audio),
            str(final_audio),
        )

    engine_router.generate = (
        fake_router_generate
    )

    service.apply_audio_controls = (
        fake_apply_controls
    )

    result = service.generate_speech(
        db=fake_database,
        voice_id=fake_voice.id,
        text=source_input,
        speed=1.0,
        volume=1.0,
        bass=0.0,
        requested_engine="indicf5",
        allow_fallback=False,
    )

    final_output_path = (
        service.output_folder
        / result["output_filename"]
    ).resolve()

    check(
        "Normalised text returned to API",
        result["text"]
        == expected_history_text,
        (
            f"Expected {expected_history_text!r}; "
            f"received {result['text']!r}"
        ),
    )

    check(
        "Normalised text stored in history model",
        fake_database.added is not None
        and fake_database.added.text
        == expected_history_text,
    )

    check(
        "Prepared text sent to speech engine",
        captured_router_arguments.get("text")
        == expected_synthesis_text,
        (
            "Received: "
            f"{captured_router_arguments.get('text')!r}"
        ),
    )

    check(
        "Normalised source sent for language detection",
        captured_router_arguments.get(
            "detection_text"
        )
        == expected_history_text,
    )

    check(
        "Reference transcript normalised without acronym expansion",
        captured_router_arguments.get(
            "prompt_text"
        )
        == expected_prompt_text,
    )

    check(
        "Detected language remains mixed",
        result["detected_language"]
        == "mixed",
    )

    check(
        "Explicit IndicF5 routing preserved",
        result["engine_used"]
        == "indicf5"
        and result["routing_reason"]
        == "explicit_indicf5"
        and result["fallback_used"]
        is False,
    )

    check(
        "Fake transaction committed",
        fake_database.committed
        and not fake_database.rolled_back,
    )

    check(
        "Final WAV created",
        final_output_path.exists()
        and final_output_path.stat().st_size > 44,
    )

    limit_database = FakeDatabase(
        fake_voice
    )

    limit_error: ValueError | None = None

    try:
        service.generate_speech(
            db=limit_database,
            voice_id=fake_voice.id,
            text="a" * 1501,
            requested_engine="indicf5",
            allow_fallback=False,
        )

    except ValueError as error:
        limit_error = error

    check(
        "Single-request limit enforced by TTS service",
        limit_error is not None
        and "1500" in str(limit_error),
        (
            "Error: "
            + (
                str(limit_error)
                if limit_error
                else "No error"
            )
        ),
    )

    check(
        "Over-limit input rejected before database lookup",
        not limit_database.query_called,
    )

    check(
        "Preprocessor source remains idempotent",
        TextPreprocessor.normalize(
            expected_history_text
        )
        == expected_history_text,
    )

finally:
    engine_router.generate = (
        original_router_generate
    )

    service.apply_audio_controls = (
        original_apply_controls
    )

    if (
        final_output_path is not None
        and final_output_path.exists()
    ):
        final_output_path.unlink()

    if reference_path.exists():
        reference_path.unlink()

print()
print("=" * 80)
print(
    "MILESTONE 10.5 PREPROCESSING–TTS INTEGRATION: PASSED"
)
print("=" * 80)
print("Checks passed:", checks_passed)
