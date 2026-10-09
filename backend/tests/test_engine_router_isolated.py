from pathlib import Path
from tempfile import TemporaryDirectory

from app.services.engine_router import (
    AllEnginesUnavailableError,
    EngineRouter,
)


class FakeCosyVoice:
    def __init__(
        self,
        *,
        unavailable: bool = False,
        generation_failure: bool = False,
    ) -> None:
        self.unavailable = unavailable
        self.generation_failure = generation_failure
        self.load_calls = 0
        self.generate_calls = 0

    def load(self) -> dict:
        self.load_calls += 1

        if self.unavailable:
            raise RuntimeError(
                "Fake CosyVoice unavailable."
            )

        return {
            "model_loaded": True,
        }

    def generate(
        self,
        reference_audio: str,
        prompt_text: str,
        text: str,
        output_path: str,
        speed: float = 1.0,
    ) -> None:
        self.generate_calls += 1

        if self.generation_failure:
            raise RuntimeError(
                "Fake CosyVoice generation failure."
            )

        Path(output_path).write_bytes(
            b"fake-cosyvoice-audio"
        )


class FakeIndicF5:
    def __init__(
        self,
        *,
        unavailable: bool = False,
        generation_failure: bool = False,
    ) -> None:
        self.unavailable = unavailable
        self.generation_failure = generation_failure
        self.load_calls = 0
        self.generate_calls = 0

    def load(self) -> dict:
        self.load_calls += 1

        if self.unavailable:
            raise RuntimeError(
                "Fake IndicF5 unavailable."
            )

        return {
            "status": "healthy",
            "model_loaded": True,
        }

    def generate(
        self,
        reference_audio: str,
        prompt_text: str,
        text: str,
        output_path: str,
        speed: float = 1.0,
        language: str = "auto",
    ) -> dict:
        self.generate_calls += 1

        if self.generation_failure:
            raise RuntimeError(
                "Fake IndicF5 generation failure."
            )

        Path(output_path).write_bytes(
            b"fake-indicf5-audio"
        )

        return {
            "engine": "indicf5",
            "device": "cuda:0",
            "language": language,
            "output_path": output_path,
            "speed_requested": speed,
            "speed_applied_by_engine": False,
        }


def run_generation(
    router: EngineRouter,
    output_path: Path,
    *,
    text: str,
    requested_engine: str = "auto",
    allow_fallback: bool = True,
) -> dict:
    return router.generate(
        requested_engine=requested_engine,
        allow_fallback=allow_fallback,
        original_reference_audio=(
            "original_reference.wav"
        ),
        cosyvoice_reference_audio=(
            "normalized_reference.wav"
        ),
        prompt_text="Reference transcript.",
        text=text,
        output_path=str(output_path),
        speed=1.0,
    )


def check(
    name: str,
    condition: bool,
) -> None:
    if not condition:
        raise AssertionError(
            f"{name}: FAILED"
        )

    print(f"{name}: PASSED")


print("=" * 80)
print("ENGINE ROUTER UTF-8 ISOLATED TESTS")
print("=" * 80)

language_samples = (
    (
        "English",
        "Hello everyone",
        "english",
    ),
    (
        "Telugu",
        "అందరికీ నమస్కారం",
        "telugu",
    ),
    (
        "Mixed",
        "Browser లో URL type చేయండి",
        "mixed",
    ),
)

for name, text, expected in language_samples:
    detected = EngineRouter.detect_language(
        text
    )

    print(
        f"{name} text:",
        repr(text),
    )
    print(
        f"{name} code points:",
        [
            f"U+{ord(character):04X}"
            for character in text
            if not character.isspace()
        ],
    )
    print(
        f"{name} detected:",
        detected,
    )

    check(
        f"{name} detection",
        detected == expected,
    )

with TemporaryDirectory() as directory:
    temporary_directory = Path(directory)

    # Explicit CosyVoice
    cosy = FakeCosyVoice()
    indic = FakeIndicF5()

    router = EngineRouter(
        cosyvoice=cosy,
        indicf5=indic,
    )

    result = run_generation(
        router,
        temporary_directory / "explicit_cosy.wav",
        text="Hello",
        requested_engine="cosyvoice",
    )

    check(
        "Explicit CosyVoice",
        (
            result["engine_used"] == "cosyvoice"
            and result["fallback_used"] is False
            and cosy.generate_calls == 1
            and indic.generate_calls == 0
        ),
    )

    # Explicit IndicF5
    cosy = FakeCosyVoice()
    indic = FakeIndicF5()

    router = EngineRouter(
        cosyvoice=cosy,
        indicf5=indic,
    )

    result = run_generation(
        router,
        temporary_directory / "explicit_indic.wav",
        text="Hello",
        requested_engine="indicf5",
    )

    check(
        "Explicit IndicF5",
        (
            result["engine_used"] == "indicf5"
            and result["fallback_used"] is False
            and cosy.generate_calls == 0
            and indic.generate_calls == 1
        ),
    )

    # Auto English
    cosy = FakeCosyVoice()
    indic = FakeIndicF5()

    router = EngineRouter(
        cosyvoice=cosy,
        indicf5=indic,
    )

    result = run_generation(
        router,
        temporary_directory / "auto_english.wav",
        text="How does the browser work?",
    )

    check(
        "Auto English",
        (
            result["detected_language"] == "english"
            and result["engine_used"] == "cosyvoice"
            and result["fallback_used"] is False
        ),
    )

    # Auto Telugu
    cosy = FakeCosyVoice()
    indic = FakeIndicF5()

    router = EngineRouter(
        cosyvoice=cosy,
        indicf5=indic,
    )

    result = run_generation(
        router,
        temporary_directory / "auto_telugu.wav",
        text="బ్రౌజర్ ఎలా పనిచేస్తుంది?",
    )

    check(
        "Auto Telugu",
        (
            result["detected_language"] == "telugu"
            and result["engine_used"] == "indicf5"
            and result["fallback_used"] is False
        ),
    )

    # Auto Mixed
    cosy = FakeCosyVoice()
    indic = FakeIndicF5()

    router = EngineRouter(
        cosyvoice=cosy,
        indicf5=indic,
    )

    result = run_generation(
        router,
        temporary_directory / "auto_mixed.wav",
        text="Browser లో URL type చేయండి.",
    )

    check(
        "Auto Mixed",
        (
            result["detected_language"] == "mixed"
            and result["engine_used"] == "indicf5"
            and result["quality_warning"] is not None
        ),
    )

    # Unavailable English primary -> IndicF5 fallback
    cosy = FakeCosyVoice(
        unavailable=True
    )
    indic = FakeIndicF5()

    router = EngineRouter(
        cosyvoice=cosy,
        indicf5=indic,
    )

    result = run_generation(
        router,
        temporary_directory / "fallback.wav",
        text="English fallback test.",
    )

    check(
        "Unavailable-primary fallback",
        (
            result["engine_used"] == "indicf5"
            and result["fallback_used"] is True
            and len(result["failed_attempts"]) == 1
        ),
    )

    # Generation failure -> fallback
    cosy = FakeCosyVoice(
        generation_failure=True
    )
    indic = FakeIndicF5()

    router = EngineRouter(
        cosyvoice=cosy,
        indicf5=indic,
    )

    result = run_generation(
        router,
        temporary_directory
        / "generation_failure_fallback.wav",
        text="Generation failure fallback.",
    )

    check(
        "Generation-failure fallback",
        (
            result["engine_used"] == "indicf5"
            and result["fallback_used"] is True
            and result["failed_attempts"][0][
                "category"
            ]
            == "generation"
        ),
    )

    # Fallback disabled
    cosy = FakeCosyVoice(
        unavailable=True
    )
    indic = FakeIndicF5()

    router = EngineRouter(
        cosyvoice=cosy,
        indicf5=indic,
    )

    fallback_disabled_passed = False

    try:
        run_generation(
            router,
            temporary_directory
            / "fallback_disabled.wav",
            text="No fallback.",
            allow_fallback=False,
        )

    except AllEnginesUnavailableError:
        fallback_disabled_passed = (
            indic.generate_calls == 0
        )

    check(
        "Fallback disabled",
        fallback_disabled_passed,
    )

    # Explicit request stays strict
    cosy = FakeCosyVoice(
        unavailable=True
    )
    indic = FakeIndicF5()

    router = EngineRouter(
        cosyvoice=cosy,
        indicf5=indic,
    )

    explicit_strict_passed = False

    try:
        run_generation(
            router,
            temporary_directory
            / "strict_explicit.wav",
            text="Strict explicit request.",
            requested_engine="cosyvoice",
            allow_fallback=True,
        )

    except AllEnginesUnavailableError:
        explicit_strict_passed = (
            indic.generate_calls == 0
        )

    check(
        "Explicit engine strictness",
        explicit_strict_passed,
    )

    # Both services unavailable
    cosy = FakeCosyVoice(
        unavailable=True
    )
    indic = FakeIndicF5(
        unavailable=True
    )

    router = EngineRouter(
        cosyvoice=cosy,
        indicf5=indic,
    )

    both_unavailable_passed = False

    try:
        run_generation(
            router,
            temporary_directory
            / "both_unavailable.wav",
            text="Both unavailable.",
        )

    except AllEnginesUnavailableError:
        both_unavailable_passed = True

    check(
        "Both engines unavailable",
        both_unavailable_passed,
    )

print("\n" + "=" * 80)
print("ENGINE ROUTER UTF-8 ISOLATED TESTS: PASSED")
print("=" * 80)
