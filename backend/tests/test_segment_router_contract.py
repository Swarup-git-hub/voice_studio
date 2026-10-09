from __future__ import annotations

from app.ai.segmenter import TextSegmenter
from app.services.segment_router import SegmentRouter
from app.services.segment_router import SegmentRoutingDecision


checks_passed = 0
router = SegmentRouter()


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


def check_raises(
    name: str,
    expected_error: type[BaseException],
    function,
    message_marker: str,
) -> None:
    global checks_passed

    try:
        function()

    except expected_error as error:
        if message_marker not in str(error):
            raise AssertionError(
                f"{name}: wrong message\n"
                f"Expected marker: {message_marker!r}\n"
                f"Actual: {str(error)!r}"
            ) from error

        checks_passed += 1
        print(f"{name}: PASSED")
        return

    except Exception as error:
        raise AssertionError(
            f"{name}: expected "
            f"{expected_error.__name__}, received "
            f"{type(error).__name__}: {error}"
        ) from error

    raise AssertionError(
        f"{name}: expected "
        f"{expected_error.__name__}, "
        "but no exception was raised."
    )


def one_segment(
    text: str,
):
    segments = TextSegmenter.segment(
        text
    )

    if len(segments) != 1:
        raise AssertionError(
            "The test expected exactly one segment."
        )

    return segments[0]


print("=" * 84)
print("MILESTONE 10.6 SEGMENT ROUTER CONTRACT")
print("=" * 84)

english_segment = one_segment(
    "Open the browser and enter a URL."
)

english = router.plan_segment(
    english_segment
)

check(
    "English classification",
    english.detected_language
    == "english",
)

check(
    "English Auto primary is CosyVoice",
    english.primary_engine
    == "cosyvoice",
)

check(
    "English Auto fallback is IndicF5",
    english.secondary_engine
    == "indicf5",
)

check(
    "English routing reason",
    english.routing_reason
    == "auto_english_cosyvoice_primary",
)

telugu_segment = one_segment(
    "ఇది తెలుగు వాక్యం."
)

telugu = router.plan_segment(
    telugu_segment
)

check(
    "Native Telugu classification",
    telugu.detected_language
    == "telugu",
)

check(
    "Telugu Auto plan",
    telugu.engine_plan
    == (
        "indicf5",
        "cosyvoice",
    ),
)

mixed_segment = one_segment(
    "బ్రౌజర్‌లో URL టైప్ చేయండి."
)

mixed = router.plan_segment(
    mixed_segment
)

check(
    "Mixed classification",
    mixed.detected_language
    == "mixed",
)

check(
    "Mixed Auto plan",
    mixed.engine_plan
    == (
        "indicf5",
        "cosyvoice",
    ),
)

check(
    "Mixed quality warning preserved",
    mixed.quality_warning
    is not None,
)

romanized_segment = one_segment(
    (
        "Browser lo URL type chesi "
        "Enter kodithe page open avuthundi."
    )
)

romanized = router.plan_segment(
    romanized_segment
)

check(
    "Romanized Telugu classification",
    romanized.detected_language
    == "romanized_telugu",
)

check(
    "Romanized Telugu engine language",
    romanized.engine_language
    == "telugu",
)

check(
    "Romanized Telugu Auto plan",
    romanized.engine_plan
    == (
        "indicf5",
        "cosyvoice",
    ),
)

check(
    "Romanized Telugu routing reason",
    romanized.routing_reason
    == (
        "auto_romanized_telugu_"
        "indicf5_primary"
    ),
)

check(
    "Romanized Telugu warning",
    romanized.quality_warning
    is not None,
)

ordinary_english = router.plan_segment(
    one_segment(
        "Open the browser and enter the address."
    )
)

check(
    "Ordinary English is not Romanized Telugu",
    ordinary_english.detected_language
    == "english",
)

explicit_cosy = router.plan_segment(
    mixed_segment,
    requested_engine="cosyvoice",
    allow_fallback=True,
)

check(
    "Explicit CosyVoice remains strict",
    explicit_cosy.engine_plan
    == (
        "cosyvoice",
    ),
)

check(
    "Explicit CosyVoice fallback disabled",
    explicit_cosy.fallback_allowed
    is False,
)

check(
    "Explicit CosyVoice reason",
    explicit_cosy.routing_reason
    == "explicit_cosyvoice",
)

explicit_indic = router.plan_segment(
    english_segment,
    requested_engine="indicf5",
    allow_fallback=True,
)

check(
    "Explicit IndicF5 remains strict",
    explicit_indic.engine_plan
    == (
        "indicf5",
    ),
)

auto_without_fallback = router.plan_segment(
    english_segment,
    requested_engine="auto",
    allow_fallback=False,
)

check(
    "Auto without fallback has one engine",
    auto_without_fallback.engine_plan
    == (
        "cosyvoice",
    ),
)

check(
    "Auto fallback metadata is false",
    auto_without_fallback.fallback_allowed
    is False,
)

multi_segments = TextSegmenter.segment(
    (
        "This is an English sentence."
        "\n\n"
        "ఇది తెలుగు వాక్యం."
        "\n\n"
        "Browser lo URL type chesi Enter kodithe."
    )
)

multi_decisions = router.plan_segments(
    multi_segments
)

check(
    "Multiple segments are all planned",
    len(multi_decisions)
    == len(multi_segments)
    == 3,
)

check(
    "Routing decision indexes preserved",
    [
        decision.segment_index
        for decision in multi_decisions
    ]
    == [
        0,
        1,
        2,
    ],
)

check(
    "Paragraph indexes preserved",
    [
        decision.paragraph_index
        for decision in multi_decisions
    ]
    == [
        0,
        1,
        2,
    ],
)

check(
    "Multiple segment languages",
    [
        decision.detected_language
        for decision in multi_decisions
    ]
    == [
        "english",
        "telugu",
        "romanized_telugu",
    ],
)

check(
    "Routing decisions use immutable data objects",
    all(
        isinstance(
            decision,
            SegmentRoutingDecision,
        )
        for decision in multi_decisions
    ),
)

summary = router.summarize(
    multi_decisions
)

check(
    "Summary segment count",
    summary["segment_count"] == 3,
)

check(
    "Summary primary engines",
    summary["primary_engines"]
    == [
        "cosyvoice",
        "indicf5",
        "indicf5",
    ],
)

check(
    "Summary detects quality warning",
    summary["has_quality_warning"]
    is True,
)

repeated_decisions = router.plan_segments(
    multi_segments
)

check(
    "Segment planning is deterministic",
    repeated_decisions
    == multi_decisions,
)

check(
    "Source text remains readable",
    english.source_text
    == "Open the browser and enter a URL.",
)

check(
    "Synthesis text remains prepared",
    "U R L"
    in english.synthesis_text,
)

check_raises(
    "Invalid engine is rejected",
    ValueError,
    lambda: router.plan_segment(
        english_segment,
        requested_engine="unknown",
    ),
    "auto, cosyvoice, indicf5",
)

check_raises(
    "Empty segment list is rejected",
    ValueError,
    lambda: router.plan_segments(
        []
    ),
    "At least one text segment",
)

check_raises(
    "Empty routing summary is rejected",
    ValueError,
    lambda: router.summarize(
        []
    ),
    "At least one routing decision",
)

print()
print("=" * 84)
print(
    "MILESTONE 10.6 SEGMENT ROUTER CONTRACT: PASSED"
)
print("=" * 84)
print("Checks passed:", checks_passed)
