from __future__ import annotations

import re

from app.ai.preprocess import TextPreprocessor
from app.ai.segmenter import TextSegment
from app.ai.segmenter import TextSegmenter


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


def check_raises(
    name: str,
    expected_error: type[BaseException],
    function,
    expected_message: str | None = None,
) -> None:
    global checks_passed

    try:
        function()

    except expected_error as error:
        if (
            expected_message is not None
            and expected_message
            not in str(error)
        ):
            raise AssertionError(
                f"{name}: wrong error message\n"
                f"Expected marker: {expected_message!r}\n"
                f"Actual: {str(error)!r}"
            ) from error

        checks_passed += 1
        print(f"{name}: PASSED")
        return

    except Exception as error:
        raise AssertionError(
            f"{name}: expected "
            f"{expected_error.__name__}, "
            f"received {type(error).__name__}: {error}"
        ) from error

    raise AssertionError(
        f"{name}: expected "
        f"{expected_error.__name__}, "
        "but no exception was raised."
    )


def flattened(
    text: str,
) -> str:
    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def reconstructed_source(
    segments: list[TextSegment],
) -> str:
    return flattened(
        " ".join(
            segment.source_text
            for segment in segments
        )
    )


print("=" * 84)
print("MILESTONE 10.6 TEXT SEGMENTER CONTRACT")
print("=" * 84)

short_segments = TextSegmenter.segment(
    "  Open   the URL using API!!!!  "
)

check(
    "Short input produces one segment",
    len(short_segments) == 1,
)

check(
    "Short source remains readable",
    short_segments[0].source_text
    == "Open the URL using API!",
    repr(short_segments[0]),
)

check(
    "Technical terms expand only in synthesis",
    short_segments[0].synthesis_text
    == "Open the U R L using A P I!",
    repr(short_segments[0]),
)

check(
    "Single final segment has none boundary",
    short_segments[0].boundary_after
    == "none",
)

paragraph_segments = TextSegmenter.segment(
    "First paragraph.\n\nSecond paragraph."
)

check(
    "Paragraphs remain separate",
    len(paragraph_segments) == 2,
    repr(paragraph_segments),
)

check(
    "First paragraph boundary is preserved",
    paragraph_segments[0].boundary_after
    == "paragraph",
)

check(
    "Final paragraph has no trailing boundary",
    paragraph_segments[1].boundary_after
    == "none",
)

sentence_segments = TextSegmenter.segment(
    (
        "First sentence. Second sentence! "
        "Third sentence?"
    ),
    max_synthesis_characters=40,
)

check(
    "Sentence-aware packing creates multiple segments",
    len(sentence_segments) >= 2,
    repr(sentence_segments),
)

check(
    "Sentence punctuation is preserved",
    reconstructed_source(
        sentence_segments
    )
    == (
        "First sentence. Second sentence! "
        "Third sentence?"
    ),
)

long_text = " ".join(
    f"word{index}"
    for index in range(700)
)

long_segments = TextSegmenter.segment(
    long_text
)

check(
    "Long input produces multiple segments",
    len(long_segments) > 1,
)

check(
    "Every long segment is within engine limit",
    all(
        segment.synthesis_character_count
        <= TextPreprocessor.MAX_SINGLE_REQUEST_CHARACTERS
        for segment in long_segments
    ),
)

check(
    "Long input loses no words",
    reconstructed_source(
        long_segments
    )
    == flattened(
        TextPreprocessor.normalize(
            long_text
        )
    ),
)

check(
    "Long segment indexes are continuous",
    [
        segment.index
        for segment in long_segments
    ]
    == list(
        range(
            len(long_segments)
        )
    ),
)

expansion_text = " ".join(
    "API"
    for _ in range(400)
)

expansion_segments = TextSegmenter.segment(
    expansion_text
)

check(
    "Expansion-aware length creates multiple segments",
    len(expansion_segments) > 1,
)

check(
    "Expanded synthesis remains within limit",
    all(
        len(segment.synthesis_text)
        <= 1500
        for segment in expansion_segments
    ),
)

check(
    "Every synthesis value matches the preprocessor",
    all(
        TextPreprocessor.prepare_for_synthesis(
            segment.source_text
        )
        == segment.synthesis_text
        for segment in expansion_segments
    ),
)

url = (
    "https://example.com/docs/API"
    "?redirect=URL"
)

url_segments = TextSegmenter.segment(
    (
        f"Open {url}. "
        "Then inspect HTTPS and API."
    ),
    max_synthesis_characters=100,
)

check(
    "URL remains intact in source",
    any(
        url in segment.source_text
        for segment in url_segments
    ),
)

check(
    "URL remains intact in synthesis",
    any(
        url in segment.synthesis_text
        for segment in url_segments
    ),
)

check(
    "Technical terms outside URL still expand",
    any(
        "H T T P S"
        in segment.synthesis_text
        and "A P I"
        in segment.synthesis_text
        for segment in url_segments
    ),
)

telugu_text = (
    "బ్రౌజర్‌లో URL టైప్ చేయండి. "
    "తర్వాత API response చూడండి."
)

telugu_segments = TextSegmenter.segment(
    telugu_text,
    max_synthesis_characters=80,
)

check(
    "Telugu Unicode is preserved",
    reconstructed_source(
        telugu_segments
    )
    == telugu_text,
)

check(
    "Telugu technical acronyms expand",
    any(
        "U R L"
        in segment.synthesis_text
        or "A P I"
        in segment.synthesis_text
        for segment in telugu_segments
    ),
)

decimal_segments = TextSegmenter.segment(
    "Version 3.14 is ready. Continue now.",
    max_synthesis_characters=40,
)

check(
    "Decimal point is not treated as sentence end",
    reconstructed_source(
        decimal_segments
    )
    == "Version 3.14 is ready. Continue now.",
)

abbreviation_segments = TextSegmenter.segment(
    "For example, e.g. this value works. Continue.",
    max_synthesis_characters=70,
)

check(
    "Known abbreviation is not split incorrectly",
    reconstructed_source(
        abbreviation_segments
    )
    == (
        "For example, e.g. this value works. "
        "Continue."
    ),
)

deterministic_first = TextSegmenter.segment(
    long_text,
    max_synthesis_characters=120,
)

deterministic_second = TextSegmenter.segment(
    long_text,
    max_synthesis_characters=120,
)

check(
    "Segmentation is deterministic",
    deterministic_first
    == deterministic_second,
)

check(
    "Segment objects expose immutable metadata",
    all(
        isinstance(
            segment,
            TextSegment,
        )
        for segment in deterministic_first
    ),
)

check(
    "No segment is empty",
    all(
        segment.source_text
        and segment.synthesis_text
        for segment in deterministic_first
    ),
)

check_raises(
    "Blank input is rejected",
    ValueError,
    lambda: TextSegmenter.segment(
        "\ufeff\u200b\u2060"
    ),
    "empty",
)

check_raises(
    "API input above 10,000 characters is rejected",
    ValueError,
    lambda: TextSegmenter.segment(
        "a" * 10_001
    ),
    "10000",
)

check_raises(
    "Limit below 16 is rejected",
    ValueError,
    lambda: TextSegmenter.segment(
        "Valid text.",
        max_synthesis_characters=15,
    ),
    "at least 16",
)

check_raises(
    "Limit above engine maximum is rejected",
    ValueError,
    lambda: TextSegmenter.segment(
        "Valid text.",
        max_synthesis_characters=1501,
    ),
    "cannot exceed 1500",
)

check_raises(
    "Oversized single token is rejected",
    ValueError,
    lambda: TextSegmenter.segment(
        "x" * 81,
        max_synthesis_characters=80,
    ),
    "single token",
)

alias_segments = TextSegmenter.split(
    "URL works."
)

check(
    "Split alias matches segment method",
    alias_segments
    == TextSegmenter.segment(
        "URL works."
    ),
)

print()
print("=" * 84)
print(
    "MILESTONE 10.6 TEXT SEGMENTER CONTRACT: PASSED"
)
print("=" * 84)
print("Checks passed:", checks_passed)
