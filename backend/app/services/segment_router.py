from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from typing import Sequence
from typing import cast

from app.ai.preprocess import TextPreprocessor
from app.ai.segmenter import SegmentBoundary
from app.ai.segmenter import TextSegment
from app.services.engine_router import DetectedLanguage
from app.services.engine_router import EngineRouter
from app.services.engine_router import engine_router


SegmentLanguage = Literal[
    "english",
    "telugu",
    "mixed",
    "romanized_telugu",
]


@dataclass(
    frozen=True,
    slots=True,
)
class SegmentRoutingDecision:
    """
    Routing metadata for one text segment.

    This object plans generation only. It does not call an engine,
    create WAV files, or write history records.
    """

    segment_index: int
    paragraph_index: int

    source_text: str
    synthesis_text: str
    boundary_after: SegmentBoundary

    requested_engine: str
    detected_language: SegmentLanguage
    engine_language: DetectedLanguage

    engine_plan: tuple[str, ...]
    routing_reason: str
    quality_warning: str | None
    fallback_allowed: bool

    @property
    def primary_engine(
        self,
    ) -> str:
        return self.engine_plan[0]

    @property
    def secondary_engine(
        self,
    ) -> str | None:
        if len(self.engine_plan) < 2:
            return None

        return self.engine_plan[1]


class SegmentRouter:
    """
    Classify and plan each completed TextSegment independently.

    The existing EngineRouter remains the source of truth for actual
    engine order, explicit-engine strictness, and fallback policy.
    """

    ROMANIZED_TELUGU_WARNING = (
        "Romanized Telugu was detected. IndicF5 is preferred "
        "first in Auto mode, but pronunciation should be reviewed."
    )

    def __init__(
        self,
        router: EngineRouter | None = None,
    ) -> None:
        self.router = (
            router
            if router is not None
            else engine_router
        )

    def classify(
        self,
        text: str,
    ) -> SegmentLanguage:
        normalized = (
            TextPreprocessor.validate_api_text(
                text
            )
        )

        base_language = (
            self.router.detect_language(
                normalized
            )
        )

        if (
            base_language == "english"
            and TextPreprocessor.is_probably_romanized_telugu(
                normalized
            )
        ):
            return "romanized_telugu"

        return cast(
            SegmentLanguage,
            base_language,
        )

    @staticmethod
    def to_engine_language(
        detected_language: SegmentLanguage,
    ) -> DetectedLanguage:
        """
        Map the richer segment classification to the language values
        supported by the existing speech engines.
        """

        if detected_language == "romanized_telugu":
            return "telugu"

        return cast(
            DetectedLanguage,
            detected_language,
        )

    def plan_segment(
        self,
        segment: TextSegment,
        *,
        requested_engine: str = "auto",
        allow_fallback: bool = True,
    ) -> SegmentRoutingDecision:
        clean_engine = (
            requested_engine
            .strip()
            .lower()
        )

        if (
            clean_engine
            not in self.router.ALLOWED_ENGINES
        ):
            raise ValueError(
                "Engine must be one of: "
                "auto, cosyvoice, indicf5."
            )

        detected_language = self.classify(
            segment.source_text
        )

        engine_language = (
            self.to_engine_language(
                detected_language
            )
        )

        plan, routing_reason, quality_warning = (
            self.router.build_routing_plan(
                requested_engine=clean_engine,
                detected_language=engine_language,
                allow_fallback=allow_fallback,
            )
        )

        if detected_language == "romanized_telugu":
            quality_warning = (
                self.ROMANIZED_TELUGU_WARNING
            )

            if clean_engine == "auto":
                routing_reason = (
                    "auto_romanized_telugu_"
                    "indicf5_primary"
                )

        if not plan:
            raise RuntimeError(
                "The segment routing plan is empty."
            )

        fallback_allowed = (
            clean_engine == "auto"
            and allow_fallback
            and len(plan) > 1
        )

        return SegmentRoutingDecision(
            segment_index=segment.index,
            paragraph_index=(
                segment.paragraph_index
            ),
            source_text=segment.source_text,
            synthesis_text=(
                segment.synthesis_text
            ),
            boundary_after=(
                segment.boundary_after
            ),
            requested_engine=clean_engine,
            detected_language=(
                detected_language
            ),
            engine_language=engine_language,
            engine_plan=tuple(plan),
            routing_reason=routing_reason,
            quality_warning=quality_warning,
            fallback_allowed=(
                fallback_allowed
            ),
        )

    def plan_segments(
        self,
        segments: Sequence[TextSegment],
        *,
        requested_engine: str = "auto",
        allow_fallback: bool = True,
    ) -> list[SegmentRoutingDecision]:
        if not segments:
            raise ValueError(
                "At least one text segment is required."
            )

        decisions = [
            self.plan_segment(
                segment,
                requested_engine=(
                    requested_engine
                ),
                allow_fallback=(
                    allow_fallback
                ),
            )
            for segment in segments
        ]

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
                "Text segment indexes must be continuous "
                "and start at zero."
            )

        return decisions

    @staticmethod
    def summarize(
        decisions: Sequence[
            SegmentRoutingDecision
        ],
    ) -> dict[str, object]:
        if not decisions:
            raise ValueError(
                "At least one routing decision is required."
            )

        return {
            "segment_count": len(decisions),
            "languages": [
                decision.detected_language
                for decision in decisions
            ],
            "primary_engines": [
                decision.primary_engine
                for decision in decisions
            ],
            "fallback_segments": sum(
                1
                for decision in decisions
                if decision.fallback_allowed
            ),
            "has_quality_warning": any(
                decision.quality_warning
                is not None
                for decision in decisions
            ),
        }


segment_router = SegmentRouter()
