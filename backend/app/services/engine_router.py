from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from typing import Literal

from app.services.cosyvoice_engine import (
    engine as cosyvoice_engine,
)
from app.services.f5_engine import (
    IndicF5GenerationError,
    IndicF5UnavailableError,
    engine as indicf5_engine,
)


EngineChoice = Literal[
    "auto",
    "cosyvoice",
    "indicf5",
]

DetectedLanguage = Literal[
    "english",
    "telugu",
    "mixed",
]


class EngineRouterError(RuntimeError):
    """Base error raised by the engine-routing layer."""


class EngineUnavailableError(EngineRouterError):
    """Raised when a selected speech service is unavailable."""


class EngineGenerationError(EngineRouterError):
    """Raised when a service is available but generation fails."""


class AllEnginesUnavailableError(EngineUnavailableError):
    """Raised when every allowed engine is unavailable."""


class EngineRouter:
    """
    Select and execute a speech engine without changing the shared
    reference preparation, audio controls, database transaction,
    or output-history behaviour in TTSService.
    """

    ALLOWED_ENGINES = {
        "auto",
        "cosyvoice",
        "indicf5",
    }

    def __init__(
        self,
        cosyvoice: Any = None,
        indicf5: Any = None,
    ) -> None:
        self.cosyvoice = (
            cosyvoice
            if cosyvoice is not None
            else cosyvoice_engine
        )

        self.indicf5 = (
            indicf5
            if indicf5 is not None
            else indicf5_engine
        )

    # ========================================================
    # Language detection
    # ========================================================

    @staticmethod
    def detect_language(
        text: str,
    ) -> DetectedLanguage:
        """
        Detect Telugu Unicode, Latin characters, or both.

        Romanized Telugu detection and detailed technical-word
        preprocessing belong to Milestone 10.5.
        """

        clean_text = text.strip()

        if not clean_text:
            raise ValueError(
                "Speech text cannot be empty."
            )

        has_telugu = any(
            "\u0c00" <= character <= "\u0c7f"
            for character in clean_text
        )

        has_latin = bool(
            re.search(
                r"[A-Za-z]",
                clean_text,
            )
        )

        if has_telugu and has_latin:
            return "mixed"

        if has_telugu:
            return "telugu"

        return "english"

    # ========================================================
    # Routing policy
    # ========================================================

    @staticmethod
    def build_routing_plan(
        requested_engine: EngineChoice,
        detected_language: DetectedLanguage,
        allow_fallback: bool,
    ) -> tuple[
        list[str],
        str,
        str | None,
    ]:
        """
        Return:
        - ordered engine attempts
        - routing reason
        - optional quality warning
        """

        if requested_engine == "cosyvoice":
            return (
                ["cosyvoice"],
                "explicit_cosyvoice",
                None,
            )

        if requested_engine == "indicf5":
            return (
                ["indicf5"],
                "explicit_indicf5",
                None,
            )

        quality_warning: str | None = None

        if detected_language == "english":
            primary = "cosyvoice"
            secondary = "indicf5"
            reason = "auto_english_cosyvoice_primary"

        elif detected_language == "telugu":
            primary = "indicf5"
            secondary = "cosyvoice"
            reason = "auto_telugu_indicf5_primary"

        else:
            primary = "indicf5"
            secondary = "cosyvoice"
            reason = "auto_mixed_indicf5_primary"

            quality_warning = (
                "Mixed Telugu-English text is currently routed "
                "as one request. Phrase-aware routing will be "
                "added in Milestone 10.6."
            )

        plan = [primary]

        if allow_fallback:
            plan.append(secondary)

        return (
            plan,
            reason,
            quality_warning,
        )

    # ========================================================
    # Output validation
    # ========================================================

    @staticmethod
    def validate_output(
        output_path: Path,
        engine_name: str,
    ) -> None:
        if not output_path.exists():
            raise EngineGenerationError(
                f"{engine_name} completed without "
                "creating the requested WAV."
            )

        if not output_path.is_file():
            raise EngineGenerationError(
                f"{engine_name} output is not a file."
            )

        if output_path.stat().st_size <= 0:
            output_path.unlink(
                missing_ok=True
            )

            raise EngineGenerationError(
                f"{engine_name} created an empty WAV."
            )

    # ========================================================
    # CosyVoice execution
    # ========================================================

    def generate_with_cosyvoice(
        self,
        *,
        reference_audio: str,
        prompt_text: str,
        text: str,
        output_path: Path,
        speed: float,
        detected_language: DetectedLanguage,
    ) -> dict[str, Any]:
        try:
            self.cosyvoice.load()

        except (
            ValueError,
            FileNotFoundError,
        ):
            raise

        except Exception as error:
            raise EngineUnavailableError(
                f"CosyVoice is unavailable: {error}"
            ) from error

        try:
            self.cosyvoice.generate(
                reference_audio=reference_audio,
                prompt_text=prompt_text,
                text=text,
                output_path=str(output_path),
                speed=speed,
            )

        except (
            ValueError,
            FileNotFoundError,
        ):
            raise

        except Exception as error:
            raise EngineGenerationError(
                f"CosyVoice generation failed: {error}"
            ) from error

        self.validate_output(
            output_path=output_path,
            engine_name="CosyVoice",
        )

        return {
            "engine": "cosyvoice",
            "language": detected_language,
            "output_path": str(output_path),
            "speed_requested": speed,
            "speed_applied_by_engine": True,
        }

    # ========================================================
    # IndicF5 execution
    # ========================================================

    def generate_with_indicf5(
        self,
        *,
        reference_audio: str,
        prompt_text: str,
        text: str,
        output_path: Path,
        speed: float,
        detected_language: DetectedLanguage,
    ) -> dict[str, Any]:
        try:
            self.indicf5.load()

        except (
            ValueError,
            FileNotFoundError,
        ):
            raise

        except IndicF5UnavailableError as error:
            raise EngineUnavailableError(
                str(error)
            ) from error

        except Exception as error:
            raise EngineUnavailableError(
                f"IndicF5 is unavailable: {error}"
            ) from error

        try:
            result = self.indicf5.generate(
                reference_audio=reference_audio,
                prompt_text=prompt_text,
                text=text,
                output_path=str(output_path),
                speed=speed,
                language=detected_language,
            )

        except (
            ValueError,
            FileNotFoundError,
        ):
            raise

        except IndicF5UnavailableError as error:
            raise EngineUnavailableError(
                str(error)
            ) from error

        except IndicF5GenerationError as error:
            raise EngineGenerationError(
                str(error)
            ) from error

        except Exception as error:
            raise EngineGenerationError(
                f"IndicF5 generation failed: {error}"
            ) from error

        self.validate_output(
            output_path=output_path,
            engine_name="IndicF5",
        )

        return {
            **result,
            "engine": "indicf5",
            "language": detected_language,
            "output_path": str(output_path),
            "speed_requested": speed,
            "speed_applied_by_engine": False,
        }

    # ========================================================
    # Shared routing execution
    # ========================================================

    def generate(
        self,
        *,
        requested_engine: str,
        allow_fallback: bool,
        original_reference_audio: str,
        cosyvoice_reference_audio: str,
        prompt_text: str,
        text: str,
        output_path: str,
        speed: float,
        detection_text: str | None = None,
    ) -> dict[str, Any]:
        clean_engine = (
            requested_engine
            .strip()
            .lower()
        )

        if clean_engine not in self.ALLOWED_ENGINES:
            raise ValueError(
                "Engine must be one of: "
                "auto, cosyvoice, indicf5."
            )

        clean_text = text.strip()
        clean_prompt_text = prompt_text.strip()

        clean_detection_text = (
            detection_text.strip()
            if detection_text is not None
            else clean_text
        )

        if not clean_text:
            raise ValueError(
                "Speech text cannot be empty."
            )

        if not clean_prompt_text:
            raise ValueError(
                "Reference transcript cannot be empty."
            )

        if not clean_detection_text:
            raise ValueError(
                "Language-detection text cannot be empty."
            )

        if not 0.5 <= speed <= 2.0:
            raise ValueError(
                "Speed must be between 0.5 and 2.0."
            )

        detected_language = self.detect_language(
            clean_detection_text
        )

        plan, routing_reason, quality_warning = (
            self.build_routing_plan(
                requested_engine=clean_engine,
                detected_language=detected_language,
                allow_fallback=allow_fallback,
            )
        )

        destination_path = Path(
            output_path
        ).expanduser().resolve()

        destination_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        failures: list[dict[str, str]] = []

        for attempt_index, engine_name in enumerate(
            plan
        ):
            destination_path.unlink(
                missing_ok=True
            )

            try:
                if engine_name == "cosyvoice":
                    engine_result = (
                        self.generate_with_cosyvoice(
                            reference_audio=(
                                cosyvoice_reference_audio
                            ),
                            prompt_text=clean_prompt_text,
                            text=clean_text,
                            output_path=destination_path,
                            speed=speed,
                            detected_language=(
                                detected_language
                            ),
                        )
                    )

                else:
                    engine_result = (
                        self.generate_with_indicf5(
                            reference_audio=(
                                original_reference_audio
                            ),
                            prompt_text=clean_prompt_text,
                            text=clean_text,
                            output_path=destination_path,
                            speed=speed,
                            detected_language=(
                                detected_language
                            ),
                        )
                    )

            except (
                ValueError,
                FileNotFoundError,
            ):
                destination_path.unlink(
                    missing_ok=True
                )
                raise

            except EngineUnavailableError as error:
                destination_path.unlink(
                    missing_ok=True
                )

                failures.append(
                    {
                        "engine": engine_name,
                        "category": "unavailable",
                        "message": str(error),
                    }
                )

                continue

            except EngineGenerationError as error:
                destination_path.unlink(
                    missing_ok=True
                )

                failures.append(
                    {
                        "engine": engine_name,
                        "category": "generation",
                        "message": str(error),
                    }
                )

                continue

            fallback_used = attempt_index > 0

            final_reason = routing_reason

            if fallback_used and failures:
                previous_failure = failures[-1]

                final_reason = (
                    f"{routing_reason};"
                    f"fallback_after_"
                    f"{previous_failure['engine']}_"
                    f"{previous_failure['category']}"
                )

            return {
                **engine_result,
                "engine_requested": clean_engine,
                "engine_used": engine_name,
                "detected_language": (
                    detected_language
                ),
                "fallback_used": fallback_used,
                "routing_reason": final_reason,
                "quality_warning": quality_warning,
                "failed_attempts": failures,
            }

        failure_summary = "; ".join(
            (
                f"{failure['engine']} "
                f"({failure['category']}): "
                f"{failure['message']}"
            )
            for failure in failures
        )

        all_unavailable = bool(failures) and all(
            failure["category"] == "unavailable"
            for failure in failures
        )

        if all_unavailable:
            raise AllEnginesUnavailableError(
                "No permitted speech engine is available. "
                f"{failure_summary}"
            )

        raise EngineGenerationError(
            "Speech generation failed for every permitted "
            f"engine. {failure_summary}"
        )


engine_router = EngineRouter()
