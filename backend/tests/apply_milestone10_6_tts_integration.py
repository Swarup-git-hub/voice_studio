from __future__ import annotations

from pathlib import Path


TTS_PATH = Path(
    "app/services/tts_service.py"
).resolve()


def replace_once(
    source: str,
    old: str,
    new: str,
    label: str,
) -> str:
    count = source.count(old)

    if count != 1:
        raise RuntimeError(
            f"{label}: expected exactly one source marker, "
            f"but found {count}."
        )

    return source.replace(
        old,
        new,
        1,
    )


if not TTS_PATH.exists():
    raise FileNotFoundError(
        f"TTS service was not found: {TTS_PATH}"
    )

source = TTS_PATH.read_text(
    encoding="utf-8-sig"
)

original_source = source


# ------------------------------------------------------------------
# 1. Imports
# ------------------------------------------------------------------

old_imports = """from app.ai.preprocess import TextPreprocessor
from app.core.config import settings
from app.database.models import GeneratedAudio
from app.database.models import Voice
from app.services.engine_router import engine_router
"""

new_imports = """from app.ai.preprocess import TextPreprocessor
from app.ai.segmenter import TextSegmenter
from app.core.config import settings
from app.database.models import GeneratedAudio
from app.database.models import Voice
from app.services.engine_router import engine_router
from app.services.segment_router import segment_router
from app.services.segmented_synthesis import segmented_synthesis
"""

source = replace_once(
    source,
    old_imports,
    new_imports,
    "TTS imports",
)


# ------------------------------------------------------------------
# 2. Remove the old whole-request synthesis preparation
# ------------------------------------------------------------------

old_synthesis_preparation = """        synthesis_text = (
            TextPreprocessor.prepare_for_synthesis(
                clean_text
            )
        )

        romanized_telugu_signal = (
"""

new_synthesis_preparation = """        romanized_telugu_signal = (
"""

source = replace_once(
    source,
    old_synthesis_preparation,
    new_synthesis_preparation,
    "Old whole-request synthesis preparation",
)


# ------------------------------------------------------------------
# 3. Add segmentation after engine/control validation
# ------------------------------------------------------------------

old_validation_end = """        self.validate_controls(
            speed=speed,
            volume=volume,
            bass=bass,
        )

        prepared_cosyvoice_reference: Path | None = None
"""

new_validation_end = """        self.validate_controls(
            speed=speed,
            volume=volume,
            bass=bass,
        )

        text_segments = TextSegmenter.segment(
            clean_text
        )

        routing_decisions = (
            segment_router.plan_segments(
                text_segments,
                requested_engine=clean_engine,
                allow_fallback=allow_fallback,
            )
        )

        synthesis_text = "\\n".join(
            segment.synthesis_text
            for segment in text_segments
        )

        prepared_cosyvoice_reference: Path | None = None
"""

source = replace_once(
    source,
    old_validation_end,
    new_validation_end,
    "Segment preparation insertion",
)


# ------------------------------------------------------------------
# 4. Replace whole-request routing preparation
# ------------------------------------------------------------------

old_routing_preparation = """            detected_language = (
                engine_router.detect_language(
                    clean_text
                )
            )

            routing_plan, _, _ = (
                engine_router.build_routing_plan(
                    requested_engine=clean_engine,
                    detected_language=(
                        detected_language
                    ),
                    allow_fallback=allow_fallback,
                )
            )

            print("\\nROUTING PREPARATION")
            print("-" * 80)
            print(
                "Detected Language:",
                detected_language,
            )
            print(
                "Engine Plan:",
                routing_plan,
            )
"""

new_routing_preparation = """            routing_summary = (
                segment_router.summarize(
                    routing_decisions
                )
            )

            detected_languages = (
                routing_summary[
                    "languages"
                ]
            )

            routing_plan: list[str] = []

            for decision in routing_decisions:
                for engine_name in decision.engine_plan:
                    if engine_name not in routing_plan:
                        routing_plan.append(
                            engine_name
                        )

            print("\\nROUTING PREPARATION")
            print("-" * 80)
            print(
                "Segment Count:",
                len(routing_decisions),
            )
            print(
                "Detected Languages:",
                detected_languages,
            )
            print(
                "Combined Engine Plan:",
                routing_plan,
            )
"""

source = replace_once(
    source,
    old_routing_preparation,
    new_routing_preparation,
    "Routing preparation",
)


# ------------------------------------------------------------------
# 5. Replace one router call with segmented coordinator
# ------------------------------------------------------------------

old_generation_call = """            print("\\nCALLING ENGINE ROUTER...")
            print("-" * 80)

            routing_result = (
                engine_router.generate(
                    requested_engine=clean_engine,
                    allow_fallback=allow_fallback,
                    original_reference_audio=str(
                        reference_audio
                    ),
                    cosyvoice_reference_audio=str(
                        cosyvoice_reference
                    ),
                    prompt_text=clean_transcript,
                    text=synthesis_text,
                    detection_text=clean_text,
                    output_path=str(
                        raw_output_path
                    ),
                    speed=speed,
                )
            )
"""

new_generation_call = """            print(
                "\\nCALLING SEGMENTED SYNTHESIS..."
            )
            print("-" * 80)

            routing_result = (
                segmented_synthesis.generate(
                    decisions=routing_decisions,
                    requested_engine=clean_engine,
                    original_reference_audio=str(
                        reference_audio
                    ),
                    cosyvoice_reference_audio=str(
                        cosyvoice_reference
                    ),
                    prompt_text=clean_transcript,
                    output_path=str(
                        raw_output_path
                    ),
                )
            )
"""

source = replace_once(
    source,
    old_generation_call,
    new_generation_call,
    "Segmented generation call",
)


# ------------------------------------------------------------------
# Final source assertions
# ------------------------------------------------------------------

required_markers = [
    "from app.ai.segmenter import TextSegmenter",
    "from app.services.segment_router import segment_router",
    (
        "from app.services.segmented_synthesis "
        "import segmented_synthesis"
    ),
    "text_segments = TextSegmenter.segment(",
    "routing_decisions = (",
    "segment_router.plan_segments(",
    "segment_router.summarize(",
    "segmented_synthesis.generate(",
    '"Segment Count:"',
    '"Combined Engine Plan:"',
]

for marker in required_markers:
    if marker not in source:
        raise RuntimeError(
            f"Required integration marker is missing: {marker}"
        )

forbidden_markers = [
    "CALLING ENGINE ROUTER...",
    "text=synthesis_text,\n"
    "                    detection_text=clean_text,",
]

for marker in forbidden_markers:
    if marker in source:
        raise RuntimeError(
            f"Obsolete integration marker remains: {marker}"
        )

if source == original_source:
    raise RuntimeError(
        "The integration patch made no changes."
    )

TTS_PATH.write_text(
    source,
    encoding="utf-8",
    newline="\n",
)

print(
    "Milestone 10.6.6B TTS source integration: APPLIED"
)
