from __future__ import annotations

import tempfile
import wave
from array import array
from pathlib import Path
from typing import Any

from app.ai.segmenter import TextSegmenter
from app.services.engine_router import EngineGenerationError
from app.services.engine_router import EngineUnavailableError
from app.services.segment_router import SegmentRouter
from app.services.segmented_synthesis import (
    SegmentedSynthesisCoordinator,
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
            + (f"\n{detail}" if detail else "")
        )

    checks_passed += 1
    print(f"{name}: PASSED")


def write_test_wav(
    path: Path,
    amplitude: int,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    samples = array(
        "h",
        [amplitude],
    ) * 2400

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


class FakeEngineRouter:
    ALLOWED_ENGINES = {
        "auto",
        "cosyvoice",
        "indicf5",
    }

    def __init__(self) -> None:
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

        engine_name = str(
            kwargs["requested_engine"]
        )

        detection_text = str(
            kwargs["detection_text"]
        )

        if (
            "Browser lo" in detection_text
            and engine_name == "indicf5"
        ):
            raise EngineUnavailableError(
                "Simulated IndicF5 unavailability."
            )

        amplitude = (
            4000
            if engine_name == "cosyvoice"
            else 8000
        )

        write_test_wav(
            Path(kwargs["output_path"]),
            amplitude,
        )

        return {
            "engine_requested": engine_name,
            "engine_used": engine_name,
            "detected_language": "english",
            "fallback_used": False,
            "routing_reason": (
                f"explicit_{engine_name}"
            ),
            "quality_warning": None,
            "failed_attempts": [],
            "speed_requested": kwargs["speed"],
            "speed_applied_by_engine": (
                engine_name == "cosyvoice"
            ),
        }


class AlwaysFailRouter(FakeEngineRouter):
    def generate(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.calls.append(
            dict(kwargs)
        )

        raise EngineGenerationError(
            "Simulated generation failure."
        )


print("=" * 88)
print("MILESTONE 10.6 SEGMENTED SYNTHESIS CONTRACT")
print("=" * 88)

source_text = (
    "This is an English sentence."
    "\n\n"
    "ఇది తెలుగు వాక్యం."
    "\n\n"
    "Browser lo URL type chesi "
    "Enter kodithe page open avuthundi."
)

segments = TextSegmenter.segment(
    source_text
)

decisions = SegmentRouter().plan_segments(
    segments,
    requested_engine="auto",
    allow_fallback=True,
)

check(
    "Three input segments planned",
    len(decisions) == 3,
)

check(
    "Planned languages are correct",
    [
        decision.detected_language
        for decision in decisions
    ]
    == [
        "english",
        "telugu",
        "romanized_telugu",
    ],
)

with tempfile.TemporaryDirectory(
    prefix="milestone10_6_coordinator_"
) as temporary_directory:
    root = Path(
        temporary_directory
    )

    output_path = (
        root / "combined.wav"
    )

    fake_router = FakeEngineRouter()

    coordinator = (
        SegmentedSynthesisCoordinator(
            router=fake_router
        )
    )

    result = coordinator.generate(
        decisions=decisions,
        requested_engine="auto",
        original_reference_audio=(
            str(root / "reference.wav")
        ),
        cosyvoice_reference_audio=(
            str(root / "reference.wav")
        ),
        prompt_text=(
            "Reference transcript."
        ),
        output_path=output_path,
        temporary_directory=root,
    )

    check(
        "Combined output exists",
        output_path.exists(),
    )

    with wave.open(
        str(output_path),
        "rb",
    ) as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()

    check(
        "Combined output is mono",
        channels == 1,
    )

    check(
        "Combined output is PCM16",
        sample_width == 2,
    )

    check(
        "Combined output is 24 kHz",
        sample_rate == 24_000,
    )

    check(
        "Combined frame count includes paragraph pauses",
        frame_count == 24_000,
        f"Frames={frame_count}",
    )

    check(
        "Coordinator reports three segments",
        result["segment_count"] == 3,
    )

    check(
        "Coordinator reports hybrid engine usage",
        result["engine_used"] == "hybrid",
        repr(result["engine_used"]),
    )

    check(
        "Aggregate language is mixed",
        result["detected_language"]
        == "mixed",
    )

    check(
        "Fallback is recorded",
        result["fallback_used"]
        is True,
    )

    check(
        "Engine sequence is preserved",
        [
            item["engine_used"]
            for item in result["segment_results"]
        ]
        == [
            "cosyvoice",
            "indicf5",
            "cosyvoice",
        ],
    )

    check(
        "Romanized segment used fallback",
        result[
            "segment_results"
        ][2]["fallback_used"]
        is True,
    )

    expected_fallback_reason = (
        "auto_romanized_telugu_"
        "indicf5_primary;"
        "fallback_after_"
        "indicf5_unavailable"
    )

    check(
        "Romanized fallback reason is preserved",
        result[
            "segment_results"
        ][2]["routing_reason"]
        == expected_fallback_reason,
        repr(
            result[
                "segment_results"
            ][2]["routing_reason"]
        ),
    )

    check(
        "All engine calls use native speed one",
        all(
            call["speed"] == 1.0
            for call in fake_router.calls
        ),
    )

    check(
        "Shared speed remains unapplied",
        result[
            "speed_applied_by_engine"
        ]
        is False,
    )

    check(
        "Temporary segment WAVs are cleaned",
        list(
            root.glob(
                "tts_segment_*.wav"
            )
        )
        == [],
    )

    check(
        "Join metadata reports three segments",
        result[
            "join_result"
        ]["segment_count"]
        == 3,
    )

    check(
        "Phrase-routing metadata is returned",
        str(
            result["routing_reason"]
        ).startswith(
            "segmented_phrase_routing:"
        ),
    )

    explicit_segments = (
        TextSegmenter.segment(
            "First sentence. Second sentence.",
            max_synthesis_characters=20,
        )
    )

    explicit_decisions = (
        SegmentRouter().plan_segments(
            explicit_segments,
            requested_engine="indicf5",
            allow_fallback=False,
        )
    )

    explicit_output = (
        root / "explicit.wav"
    )

    explicit_result = coordinator.generate(
        decisions=explicit_decisions,
        requested_engine="indicf5",
        original_reference_audio=(
            str(root / "reference.wav")
        ),
        cosyvoice_reference_audio=(
            str(root / "reference.wav")
        ),
        prompt_text=(
            "Reference transcript."
        ),
        output_path=explicit_output,
        temporary_directory=root,
    )

    check(
        "Explicit IndicF5 remains strict",
        explicit_result["engine_used"]
        == "indicf5",
    )

    check(
        "Explicit request uses no fallback",
        explicit_result["fallback_used"]
        is False,
    )

    failing_output = (
        root / "failing.wav"
    )

    failing_coordinator = (
        SegmentedSynthesisCoordinator(
            router=AlwaysFailRouter()
        )
    )

    failure_received = False

    try:
        failing_coordinator.generate(
            decisions=explicit_decisions,
            requested_engine="indicf5",
            original_reference_audio=(
                str(root / "reference.wav")
            ),
            cosyvoice_reference_audio=(
                str(root / "reference.wav")
            ),
            prompt_text=(
                "Reference transcript."
            ),
            output_path=failing_output,
            temporary_directory=root,
        )

    except EngineGenerationError:
        failure_received = True

    check(
        "Generation failure is propagated",
        failure_received,
    )

    check(
        "Failed combined output is removed",
        not failing_output.exists(),
    )

    check(
        "Failed temporary WAVs are cleaned",
        list(
            root.glob(
                "tts_segment_*.wav"
            )
        )
        == [],
    )

print()
print("=" * 88)
print(
    "MILESTONE 10.6 SEGMENTED SYNTHESIS CONTRACT: PASSED"
)
print("=" * 88)
print("Checks passed:", checks_passed)
