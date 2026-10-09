from __future__ import annotations

import shutil
import tempfile
import wave
from array import array
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import app.services.tts_service as tts_module
from app.ai.preprocess import TextPreprocessor


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


def write_test_wav(
    path: Path,
    *,
    amplitude: int = 5000,
    duration_ms: int = 200,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    frame_count = round(
        24_000
        * duration_ms
        / 1000
    )

    samples = array(
        "h",
        [amplitude],
    ) * frame_count

    with wave.open(
        str(path),
        "wb",
    ) as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(24_000)
        wav_file.writeframes(
            samples.tobytes()
        )


def read_wav_metadata(
    path: Path,
) -> dict[str, int]:
    with wave.open(
        str(path),
        "rb",
    ) as wav_file:
        return {
            "channels": wav_file.getnchannels(),
            "sample_width": wav_file.getsampwidth(),
            "sample_rate": wav_file.getframerate(),
            "frames": wav_file.getnframes(),
        }


class FakeQuery:
    def __init__(
        self,
        voice: Any,
    ) -> None:
        self.voice = voice

    def filter(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> FakeQuery:
        return self

    def first(
        self,
    ) -> Any:
        return self.voice


class FakeDatabase:
    def __init__(
        self,
        voice: Any,
    ) -> None:
        self.voice = voice

        self.added: list[Any] = []

        self.flush_count = 0
        self.commit_count = 0
        self.rollback_count = 0

    def query(
        self,
        _model: Any,
    ) -> FakeQuery:
        return FakeQuery(
            self.voice
        )

    def add(
        self,
        value: Any,
    ) -> None:
        self.added.append(
            value
        )

    def flush(
        self,
    ) -> None:
        self.flush_count += 1

        if self.added:
            self.added[-1].id = 9001

    def commit(
        self,
    ) -> None:
        self.commit_count += 1

    def rollback(
        self,
    ) -> None:
        self.rollback_count += 1


class FakeSegmentedSynthesis:
    def __init__(
        self,
        *,
        fail: bool = False,
    ) -> None:
        self.fail = fail

        self.calls: list[
            dict[str, Any]
        ] = []

    def generate(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.calls.append(
            dict(kwargs)
        )

        output_path = Path(
            kwargs["output_path"]
        )

        if self.fail:
            output_path.write_bytes(
                b"partial-segmented-output"
            )

            raise RuntimeError(
                "Simulated segmented synthesis failure."
            )

        write_test_wav(
            output_path,
            amplitude=7000,
        )

        decisions = list(
            kwargs["decisions"]
        )

        return {
            "engine": "hybrid",
            "engine_requested": (
                kwargs["requested_engine"]
            ),
            "engine_used": "hybrid",
            "detected_language": "mixed",
            "fallback_used": False,
            "routing_reason": (
                "segmented_phrase_routing:test"
            ),
            "quality_warning": None,
            "failed_attempts": [],
            "speed_requested": 1.0,
            "speed_applied_by_engine": False,
            "output_path": str(
                output_path
            ),
            "segment_count": len(
                decisions
            ),
            "segment_results": [],
            "join_result": {
                "segment_count": len(
                    decisions
                ),
            },
        }


print("=" * 88)
print("MILESTONE 10.6 SEGMENTED TTS TRANSACTION CONTRACT")
print("=" * 88)

english_text = (
    "The backend API receives an HTTP request "
    "and returns a JSON response. "
) * 45

telugu_text = (
    "బ్రౌజర్‌లో URL టైప్ చేస్తే సర్వర్ "
    "response పంపుతుంది. "
) * 25

request_text = (
    english_text
    + "\n\n"
    + telugu_text
)

clean_request_text = (
    TextPreprocessor.validate_api_text(
        request_text
    )
)

check(
    "Test input exceeds one engine request",
    len(clean_request_text) > 1500,
    f"Characters={len(clean_request_text)}",
)

original_settings = (
    tts_module.settings
)

original_coordinator = (
    tts_module.segmented_synthesis
)

try:
    with tempfile.TemporaryDirectory(
        prefix="milestone10_6_transaction_"
    ) as temporary_directory:
        root = Path(
            temporary_directory
        )

        voice_folder = (
            root / "voices"
        )

        output_folder = (
            root / "outputs"
        )

        voice_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        reference_path = (
            voice_folder
            / "reference.wav"
        )

        write_test_wav(
            reference_path,
            amplitude=3000,
        )

        voice = SimpleNamespace(
            id=10,
            voice_name="Transaction Test Voice",
            wav_filename="reference.wav",
            transcript="Reference transcript for testing.",
        )

        tts_module.settings = (
            SimpleNamespace(
                VOICE_FOLDER=str(
                    voice_folder
                ),
                OUTPUT_FOLDER=str(
                    output_folder
                ),
            )
        )

        # ==========================================================
        # Successful transaction
        # ==========================================================

        success_database = (
            FakeDatabase(
                voice
            )
        )

        success_coordinator = (
            FakeSegmentedSynthesis()
        )

        tts_module.segmented_synthesis = (
            success_coordinator
        )

        success_service = (
            tts_module.TTSService()
        )

        success_raw_path = (
            root / "success_raw.wav"
        )

        success_final_path = (
            output_folder
            / "success.wav"
        )

        prepared_reference_path = (
            root
            / "prepared_success_reference.wav"
        )

        control_calls: list[
            dict[str, Any]
        ] = []

        def prepare_success_reference(
            reference_audio: Path,
        ) -> Path:
            shutil.copy2(
                reference_audio,
                prepared_reference_path,
            )

            return prepared_reference_path

        def apply_success_controls(
            *,
            raw_audio: Path,
            final_audio: Path,
            volume: float,
            bass: float,
            speed: float,
            apply_speed: bool,
        ) -> None:
            control_calls.append(
                {
                    "raw_audio": raw_audio,
                    "final_audio": final_audio,
                    "volume": volume,
                    "bass": bass,
                    "speed": speed,
                    "apply_speed": apply_speed,
                }
            )

            shutil.copy2(
                raw_audio,
                final_audio,
            )

        success_service.generate_filename = (
            lambda: "success.wav"
        )

        success_service.create_temp_wav_path = (
            lambda: success_raw_path
        )

        success_service.prepare_reference_audio = (
            prepare_success_reference
        )

        success_service.apply_audio_controls = (
            apply_success_controls
        )

        success_result = (
            success_service.generate_speech(
                db=success_database,
                voice_id=10,
                text=request_text,
                speed=1.25,
                volume=1.4,
                bass=4.0,
                requested_engine="auto",
                allow_fallback=True,
            )
        )

        check(
            "Segment coordinator is called once",
            len(
                success_coordinator.calls
            )
            == 1,
        )

        coordinator_call = (
            success_coordinator.calls[0]
        )

        decisions = list(
            coordinator_call[
                "decisions"
            ]
        )

        check(
            "Long request creates multiple segments",
            len(decisions) > 1,
            f"Segments={len(decisions)}",
        )

        check(
            "Segment indexes remain continuous",
            [
                decision.segment_index
                for decision in decisions
            ]
            == list(
                range(
                    len(decisions)
                )
            ),
        )

        check(
            "Every synthesis segment stays within 1500 characters",
            all(
                len(
                    decision.synthesis_text
                )
                <= 1500
                for decision in decisions
            ),
        )

        check(
            "Requested engine reaches coordinator",
            coordinator_call[
                "requested_engine"
            ]
            == "auto",
        )

        check(
            "Reference transcript reaches coordinator",
            coordinator_call[
                "prompt_text"
            ]
            == "Reference transcript for testing.",
        )

        check(
            "Shared controls run exactly once",
            len(control_calls) == 1,
        )

        control_call = control_calls[0]

        check(
            "Requested speed reaches shared controls",
            control_call["speed"]
            == 1.25,
        )

        check(
            "Requested volume reaches shared controls",
            control_call["volume"]
            == 1.4,
        )

        check(
            "Requested bass reaches shared controls",
            control_call["bass"]
            == 4.0,
        )

        check(
            "Shared layer applies speed",
            control_call[
                "apply_speed"
            ]
            is True,
        )

        check(
            "One history object is added",
            len(
                success_database.added
            )
            == 1,
        )

        check(
            "History is flushed once",
            success_database.flush_count
            == 1,
        )

        check(
            "Transaction commits once",
            success_database.commit_count
            == 1,
        )

        check(
            "Successful transaction does not roll back",
            success_database.rollback_count
            == 0,
        )

        history_record = (
            success_database.added[0]
        )

        check(
            "History stores clean source text",
            history_record.text
            == clean_request_text,
        )

        check(
            "History stores aggregate engine",
            history_record.engine_used
            == "hybrid",
        )

        check(
            "Response stores aggregate engine",
            success_result[
                "engine_used"
            ]
            == "hybrid",
        )

        check(
            "Final output survives successful commit",
            success_final_path.exists(),
        )

        final_metadata = (
            read_wav_metadata(
                success_final_path
            )
        )

        check(
            "Final output remains 24 kHz mono PCM16",
            final_metadata[
                "sample_rate"
            ]
            == 24_000
            and final_metadata[
                "channels"
            ]
            == 1
            and final_metadata[
                "sample_width"
            ]
            == 2,
            repr(final_metadata),
        )

        check(
            "Successful raw WAV is cleaned",
            not success_raw_path.exists(),
        )

        check(
            "Prepared reference is cleaned",
            not prepared_reference_path.exists(),
        )

        # ==========================================================
        # Failed transaction
        # ==========================================================

        failure_database = (
            FakeDatabase(
                voice
            )
        )

        failure_coordinator = (
            FakeSegmentedSynthesis(
                fail=True
            )
        )

        tts_module.segmented_synthesis = (
            failure_coordinator
        )

        failure_service = (
            tts_module.TTSService()
        )

        failure_raw_path = (
            root / "failure_raw.wav"
        )

        failure_final_path = (
            output_folder
            / "failure.wav"
        )

        failure_prepared_reference = (
            root
            / "prepared_failure_reference.wav"
        )

        failure_control_calls: list[
            dict[str, Any]
        ] = []

        def prepare_failure_reference(
            reference_audio: Path,
        ) -> Path:
            shutil.copy2(
                reference_audio,
                failure_prepared_reference,
            )

            return failure_prepared_reference

        def apply_failure_controls(
            **kwargs: Any,
        ) -> None:
            failure_control_calls.append(
                dict(kwargs)
            )

        failure_service.generate_filename = (
            lambda: "failure.wav"
        )

        failure_service.create_temp_wav_path = (
            lambda: failure_raw_path
        )

        failure_service.prepare_reference_audio = (
            prepare_failure_reference
        )

        failure_service.apply_audio_controls = (
            apply_failure_controls
        )

        failure_received = False

        try:
            failure_service.generate_speech(
                db=failure_database,
                voice_id=10,
                text=request_text,
                speed=1.0,
                volume=1.0,
                bass=0.0,
                requested_engine="auto",
                allow_fallback=True,
            )

        except RuntimeError as error:
            failure_received = (
                "Simulated segmented synthesis failure"
                in str(error)
            )

        check(
            "Segment failure is propagated",
            failure_received,
        )

        check(
            "Failed coordinator is called once",
            len(
                failure_coordinator.calls
            )
            == 1,
        )

        check(
            "Controls do not run after segment failure",
            failure_control_calls == [],
        )

        check(
            "Failed transaction rolls back once",
            failure_database.rollback_count
            == 1,
        )

        check(
            "Failed transaction does not commit",
            failure_database.commit_count
            == 0,
        )

        check(
            "Failed transaction creates no history",
            failure_database.added == [],
        )

        check(
            "Partial raw WAV is cleaned after failure",
            not failure_raw_path.exists(),
        )

        check(
            "Failed final output does not exist",
            not failure_final_path.exists(),
        )

        check(
            "Failure reference copy is cleaned",
            not failure_prepared_reference.exists(),
        )

finally:
    tts_module.settings = (
        original_settings
    )

    tts_module.segmented_synthesis = (
        original_coordinator
    )


print()
print("=" * 88)
print(
    "MILESTONE 10.6 SEGMENTED TTS "
    "TRANSACTION CONTRACT: PASSED"
)
print("=" * 88)
print("Checks passed:", checks_passed)
