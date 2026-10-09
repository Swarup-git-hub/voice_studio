from __future__ import annotations

from app.ai.preprocess import TextPreprocessor


passed = 0


def check_equal(
    name: str,
    actual: object,
    expected: object,
) -> None:
    global passed

    if actual != expected:
        raise AssertionError(
            f"{name}\n"
            f"Expected: {expected!r}\n"
            f"Actual:   {actual!r}"
        )

    passed += 1
    print(f"{name}: PASSED")


def check_raises(
    name: str,
    expected_error: type[BaseException],
    function,
) -> None:
    global passed

    try:
        function()

    except expected_error:
        passed += 1
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


print("=" * 80)
print("MILESTONE 10.5 TEXT PREPROCESSOR CONTRACT")
print("=" * 80)

check_equal(
    "Whitespace and non-breaking spaces",
    TextPreprocessor.normalize(
        "  Hello\u00a0\u00a0world\t \n next  "
    ),
    "Hello world\nnext",
)

check_equal(
    "Windows and repeated line endings",
    TextPreprocessor.normalize(
        "Line one\r\n\r\n\r\nLine two"
    ),
    "Line one\n\nLine two",
)

check_equal(
    "Curly quotes and repeated punctuation",
    TextPreprocessor.normalize(
        '  “Hello”   , world!!!!  Wait……  '
    ),
    '"Hello", world! Wait...',
)

check_equal(
    "Zero-width copy artifact removal",
    TextPreprocessor.normalize(
        "Browser\u200bలో"
    ),
    "Browserలో",
)

check_equal(
    "Full-width Unicode compatibility",
    TextPreprocessor.normalize(
        "ＨＴＴＰ ＡＰＩ"
    ),
    "HTTP API",
)

telugu_with_zwnj = "తెలుగు\u200cపదం"

check_equal(
    "Telugu ZWNJ preservation",
    TextPreprocessor.normalize(
        telugu_with_zwnj
    ),
    telugu_with_zwnj,
)

normalised_once = (
    TextPreprocessor.normalize(
        "  API   text!!!! "
    )
)

check_equal(
    "Normalisation is idempotent",
    TextPreprocessor.normalize(
        normalised_once
    ),
    normalised_once,
)

check_equal(
    "Technical acronym preparation",
    TextPreprocessor.prepare_for_synthesis(
        "URL, DNS, HTTPS, API, JWT, CPU and GPU."
    ),
    (
        "U R L, D N S, H T T P S, A P I, "
        "J W T, C P U and G P U."
    ),
)

check_equal(
    "URLs remain unchanged",
    TextPreprocessor.prepare_for_synthesis(
        (
            "Open https://example.com/API "
            "using HTTPS and API."
        )
    ),
    (
        "Open https://example.com/API "
        "using H T T P S and A P I."
    ),
)

check_equal(
    "Lowercase ordinary text remains unchanged",
    TextPreprocessor.prepare_for_synthesis(
        "The api folder contains an ai example."
    ),
    "The api folder contains an ai example.",
)

check_equal(
    "Synthesis flattens paragraph whitespace",
    TextPreprocessor.prepare_for_synthesis(
        "First line.\n\nSecond line."
    ),
    "First line. Second line.",
)

check_equal(
    "Romanized Telugu positive signal",
    TextPreprocessor.is_probably_romanized_telugu(
        "Browser lo URL type chesi Enter kodithe"
    ),
    True,
)

check_equal(
    "English negative Romanized Telugu signal",
    TextPreprocessor.is_probably_romanized_telugu(
        "Open the browser and enter a URL"
    ),
    False,
)

check_equal(
    "Native Telugu is not Romanized Telugu",
    TextPreprocessor.is_probably_romanized_telugu(
        "బ్రౌజర్‌లో URL టైప్ చేయండి"
    ),
    False,
)

check_equal(
    "API boundary accepts 10,000 characters",
    len(
        TextPreprocessor.validate_api_text(
            "a" * 10_000
        )
    ),
    10_000,
)

check_raises(
    "API boundary rejects 10,001 characters",
    ValueError,
    lambda: TextPreprocessor.validate_api_text(
        "a" * 10_001
    ),
)

check_equal(
    "Single request accepts 1,500 characters",
    len(
        TextPreprocessor.prepare_for_synthesis(
            "a" * 1_500
        )
    ),
    1_500,
)

check_raises(
    "Single request rejects 1,501 characters",
    ValueError,
    lambda: TextPreprocessor.prepare_for_synthesis(
        "a" * 1_501
    ),
)

for index, blank_text in enumerate(
    (
        "",
        "   \t\n  ",
        "\ufeff\u200b\u2060",
    ),
    start=1,
):
    check_raises(
        f"Blank input variant {index}",
        ValueError,
        lambda value=blank_text: (
            TextPreprocessor.validate_api_text(
                value
            )
        ),
    )

check_raises(
    "Non-string input rejection",
    TypeError,
    lambda: TextPreprocessor.normalize(
        123  # type: ignore[arg-type]
    ),
)

check_equal(
    "Backward-compatible clean alias",
    TextPreprocessor.clean(
        "  Hello    world  "
    ),
    "Hello world",
)

check_equal(
    "Backward-compatible validate alias",
    TextPreprocessor.validate(
        "Valid speech text."
    ),
    True,
)

print()
print("=" * 80)
print(
    "MILESTONE 10.5 TEXT PREPROCESSOR CONTRACT: PASSED"
)
print("=" * 80)
print("Checks passed:", passed)
