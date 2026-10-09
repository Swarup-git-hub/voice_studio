from __future__ import annotations

import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Sequence

from app.audio.joiner import WavJoinInput
from app.audio.joiner import WavJoiner
from app.services.engine_router import (
    AllEnginesUnavailableError,
)
from app.services.engine_router import (
    EngineGenerationError,
)
from app.services.engine_router import (
    EngineRouter,
)
from app.services.engine_router import (
    EngineUnavailableError,
)
from app.services.engine_router import (
    engine_router,
)
from app.services.segment_router import (
    SegmentRoutingDecision,
)


@dataclass(
    frozen=True,
    slots=True,
)
class GeneratedSegment:
    segment_index: int
    paragraph_index: int

    source_text: str
    synthesis_text: str
    boundary_after: str

    detected_language: str
    engine_language: str

    engine_used: str
    fallback_used: bool
    routing_reason: str
    quality_warning: str | None

    output_path: Path

    failed_attempts: tuple[
        dict[str, str],
        ...,
    ]


class SegmentedSynthesisCoordinator:
    """
    Generate every planned text segment and join the resulting WAVs.

    Segment engines always receive speed=1.0. The existing TTS service
    applies speed, volume, and bass once after all segment WAVs have
    been joined.
    """

    def __init__(
        self,
        *,
        router: EngineRouter | None = None,
        joiner: type[WavJoiner] = WavJoiner,
    ) -> None:
        self.router = (
            router
            if router is not None
            else engine_router
        )

        self.joiner = joiner

    @staticmethod
    def _create_segment_path(
        temporary_directory: Path,
        segment_index: int,
    ) -> Path:
        filename = (
            f"tts_segment_{segment_index:04d}_"
            f"{uuid.uuid4().hex}.wav"
        )

        return (
            temporary_directory
            / filename
        ).resolve()

    @staticmethod
    def _delete_safely(
        path: Path | None,
    ) -> None:
        if path is None:
            return

        try:
            path.unlink(
                missing_ok=True
            )

        except OSError as error:
            print(
                "Warning: Could not delete temporary "
                f"segment WAV {path}: {error}"
            )

    @staticmethod
    def _validate_decisions(
        decisions: Sequence[
            SegmentRoutingDecision
        ],
    ) -> None:
        if not decisions:
            raise ValueError(
                "At least one segment routing decision is required."
            )

        expected_indexes = list(
            range(
                len(decisions)
            )
        )

        actual_indexes = [
            decision.segment_index
            for decision in decisions
        ]

        if actual_indexes != expected_indexes:
            raise ValueError(
                "Segment routing indexes must be continuous "
                "and start at zero."
            )

        if (
            decisions[-1].boundary_after
            != "none"
        ):
            raise ValueError(
                "The final segment must use the 'none' boundary."
            )

    @staticmethod
    def _fallback_reason(
        base_reason: str,
        failures: list[
            dict[str, str]
        ],
    ) -> str:
        if not failures:
            return base_reason

        previous_failure = failures[-1]

        return (
            f"{base_reason};"
            f"fallback_after_"
            f"{previous_failure['engine']}_"
            f"{previous_failure['category']}"
        )

    def _generate_one_segment(
        self,
        *,
        decision: SegmentRoutingDecision,
        original_reference_audio: str,
        cosyvoice_reference_audio: str,
        prompt_text: str,
        output_path: Path,
    ) -> GeneratedSegment:
        failures: list[
            dict[str, str]
        ] = []

        for attempt_index, engine_name in enumerate(
            decision.engine_plan
        ):
            output_path.unlink(
                missing_ok=True
            )

            try:
                self.router.generate(
                    requested_engine=engine_name,
                    allow_fallback=False,
                    original_reference_audio=(
                        original_reference_audio
                    ),
                    cosyvoice_reference_audio=(
                        cosyvoice_reference_audio
                    ),
                    prompt_text=prompt_text,
                    text=decision.synthesis_text,
                    detection_text=(
                        decision.source_text
                    ),
                    output_path=str(
                        output_path
                    ),
                    speed=1.0,
                )

            except EngineUnavailableError as error:
                failures.append(
                    {
                        "engine": engine_name,
                        "category": "unavailable",
                        "message": str(error),
                    }
                )

                if not decision.fallback_allowed:
                    break

                continue

            except EngineGenerationError as error:
                failures.append(
                    {
                        "engine": engine_name,
                        "category": "generation",
                        "message": str(error),
                    }
                )

                if not decision.fallback_allowed:
                    break

                continue

            if not output_path.exists():
                raise RuntimeError(
                    "A segment engine returned successfully, "
                    "but its WAV file is missing."
                )

            if output_path.stat().st_size <= 44:
                output_path.unlink(
                    missing_ok=True
                )

                raise RuntimeError(
                    "A segment engine produced an empty WAV file."
                )

            fallback_used = (
                attempt_index > 0
            )

            routing_reason = (
                decision.routing_reason
            )

            if fallback_used:
                routing_reason = (
                    self._fallback_reason(
                        decision.routing_reason,
                        failures,
                    )
                )

            return GeneratedSegment(
                segment_index=(
                    decision.segment_index
                ),
                paragraph_index=(
                    decision.paragraph_index
                ),
                source_text=(
                    decision.source_text
                ),
                synthesis_text=(
                    decision.synthesis_text
                ),
                boundary_after=(
                    decision.boundary_after
                ),
                detected_language=(
                    decision.detected_language
                ),
                engine_language=(
                    decision.engine_language
                ),
                engine_used=engine_name,
                fallback_used=(
                    fallback_used
                ),
                routing_reason=(
                    routing_reason
                ),
                quality_warning=(
                    decision.quality_warning
                ),
                output_path=output_path,
                failed_attempts=tuple(
                    failures
                ),
            )

        output_path.unlink(
            missing_ok=True
        )

        failure_summary = "; ".join(
            (
                f"{failure['engine']} "
                f"({failure['category']}): "
                f"{failure['message']}"
            )
            for failure in failures
        )

        all_unavailable = (
            bool(failures)
            and all(
                failure["category"]
                == "unavailable"
                for failure in failures
            )
        )

        message = (
            "Speech generation failed for segment "
            f"{decision.segment_index}. "
            f"{failure_summary}"
        )

        if all_unavailable:
            raise AllEnginesUnavailableError(
                message
            )

        raise EngineGenerationError(
            message
        )

    @staticmethod
    def _aggregate_language(
        generated_segments: Sequence[
            GeneratedSegment
        ],
    ) -> str:
        languages: list[str] = []

        for segment in generated_segments:
            language = (
                "telugu"
                if segment.detected_language
                == "romanized_telugu"
                else segment.detected_language
            )

            if language not in languages:
                languages.append(
                    language
                )

        if len(languages) == 1:
            return languages[0]

        return "mixed"

    @staticmethod
    def _aggregate_engine(
        generated_segments: Sequence[
            GeneratedSegment
        ],
    ) -> str:
        engines: list[str] = []

        for segment in generated_segments:
            if segment.engine_used not in engines:
                engines.append(
                    segment.engine_used
                )

        if len(engines) == 1:
            return engines[0]

        return "hybrid"

    @staticmethod
    def _aggregate_warning(
        generated_segments: Sequence[
            GeneratedSegment
        ],
    ) -> str | None:
        warnings: list[str] = []

        for segment in generated_segments:
            warning = (
                segment.quality_warning
            )

            if (
                warning is not None
                and warning not in warnings
            ):
                warnings.append(
                    warning
                )

        if not warnings:
            return None

        return " | ".join(
            warnings
        )

    def generate(
        self,
        *,
        decisions: Sequence[
            SegmentRoutingDecision
        ],
        requested_engine: str,
        original_reference_audio: str,
        cosyvoice_reference_audio: str,
        prompt_text: str,
        output_path: str | Path,
        temporary_directory: str | Path | None = None,
    ) -> dict[str, Any]:
        self._validate_decisions(
            decisions
        )

        clean_requested_engine = (
            requested_engine
            .strip()
            .lower()
        )

        if (
            clean_requested_engine
            not in self.router.ALLOWED_ENGINES
        ):
            raise ValueError(
                "Engine must be one of: "
                "auto, cosyvoice, indicf5."
            )

        clean_prompt_text = (
            prompt_text.strip()
        )

        if not clean_prompt_text:
            raise ValueError(
                "Reference transcript cannot be empty."
            )

        destination = Path(
            output_path
        ).expanduser().resolve()

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination.unlink(
            missing_ok=True
        )

        temp_root = Path(
            temporary_directory
            if temporary_directory is not None
            else tempfile.gettempdir()
        ).expanduser().resolve()

        temp_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        segment_paths: list[Path] = []

        generated_segments: list[
            GeneratedSegment
        ] = []

        try:
            for decision in decisions:
                segment_path = (
                    self._create_segment_path(
                        temp_root,
                        decision.segment_index,
                    )
                )

                segment_paths.append(
                    segment_path
                )

                generated_segment = (
                    self._generate_one_segment(
                        decision=decision,
                        original_reference_audio=(
                            original_reference_audio
                        ),
                        cosyvoice_reference_audio=(
                            cosyvoice_reference_audio
                        ),
                        prompt_text=(
                            clean_prompt_text
                        ),
                        output_path=segment_path,
                    )
                )

                generated_segments.append(
                    generated_segment
                )

            join_inputs = [
                WavJoinInput(
                    path=segment.output_path,
                    boundary_after=(
                        segment.boundary_after
                    ),
                )
                for segment
                in generated_segments
            ]

            join_result = self.joiner.join(
                join_inputs,
                destination,
            )

            if not destination.exists():
                raise RuntimeError(
                    "Segment joining completed, but the "
                    "combined raw WAV is missing."
                )

            if destination.stat().st_size <= 44:
                raise RuntimeError(
                    "The combined raw WAV is empty."
                )

            aggregate_engine = (
                self._aggregate_engine(
                    generated_segments
                )
            )

            aggregate_language = (
                self._aggregate_language(
                    generated_segments
                )
            )

            fallback_used = any(
                segment.fallback_used
                for segment
                in generated_segments
            )

            if len(generated_segments) == 1:
                routing_reason = (
                    generated_segments[
                        0
                    ].routing_reason
                )

            else:
                engine_sequence = ",".join(
                    segment.engine_used
                    for segment
                    in generated_segments
                )

                routing_reason = (
                    "segmented_phrase_routing:"
                    f"{len(generated_segments)}"
                    "_segments:"
                    f"{engine_sequence}"
                )

            return {
                "engine": aggregate_engine,
                "engine_requested": (
                    clean_requested_engine
                ),
                "engine_used": (
                    aggregate_engine
                ),
                "detected_language": (
                    aggregate_language
                ),
                "fallback_used": (
                    fallback_used
                ),
                "routing_reason": (
                    routing_reason
                ),
                "quality_warning": (
                    self._aggregate_warning(
                        generated_segments
                    )
                ),
                "failed_attempts": [
                    failure
                    for segment
                    in generated_segments
                    for failure
                    in segment.failed_attempts
                ],
                "speed_requested": 1.0,
                "speed_applied_by_engine": False,
                "output_path": str(
                    destination
                ),
                "segment_count": len(
                    generated_segments
                ),
                "segment_results": [
                    {
                        "segment_index": (
                            segment.segment_index
                        ),
                        "paragraph_index": (
                            segment.paragraph_index
                        ),
                        "source_text": (
                            segment.source_text
                        ),
                        "synthesis_text": (
                            segment.synthesis_text
                        ),
                        "boundary_after": (
                            segment.boundary_after
                        ),
                        "detected_language": (
                            segment.detected_language
                        ),
                        "engine_language": (
                            segment.engine_language
                        ),
                        "engine_used": (
                            segment.engine_used
                        ),
                        "fallback_used": (
                            segment.fallback_used
                        ),
                        "routing_reason": (
                            segment.routing_reason
                        ),
                        "quality_warning": (
                            segment.quality_warning
                        ),
                    }
                    for segment
                    in generated_segments
                ],
                "join_result": (
                    join_result
                ),
            }

        except Exception:
            destination.unlink(
                missing_ok=True
            )

            raise

        finally:
            for segment_path in segment_paths:
                self._delete_safely(
                    segment_path
                )


segmented_synthesis = (
    SegmentedSynthesisCoordinator()
)
