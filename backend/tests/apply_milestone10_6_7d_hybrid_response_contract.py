from __future__ import annotations

from pathlib import Path


backend_root = Path(__file__).resolve().parents[1]

schema_path = (
    backend_root
    / "app"
    / "database"
    / "schemas.py"
)

source = schema_path.read_text(
    encoding="utf-8"
)

class_start = source.find(
    "class GenerateSpeechResponse"
)

class_end = source.find(
    "class GeneratedAudioDeleteResponse",
    class_start,
)

if class_start < 0 or class_end < 0:
    raise RuntimeError(
        "Could not locate the GenerateSpeechResponse "
        "schema block."
    )

response_block = source[
    class_start:class_end
]

old_engine_contract = """    engine_used: Literal[
        "cosyvoice",
        "indicf5",
    ]
"""

new_engine_contract = """    engine_used: Literal[
        "cosyvoice",
        "indicf5",
        "hybrid",
    ]
"""

if '"hybrid"' not in response_block:
    if response_block.count(
        old_engine_contract
    ) != 1:
        raise RuntimeError(
            "Could not find exactly one engine_used "
            "Literal contract inside "
            "GenerateSpeechResponse."
        )

    updated_block = response_block.replace(
        old_engine_contract,
        new_engine_contract,
        1,
    )

    source = (
        source[:class_start]
        + updated_block
        + source[class_end:]
    )

    schema_path.write_text(
        source,
        encoding="utf-8",
    )

updated_source = schema_path.read_text(
    encoding="utf-8"
)

updated_start = updated_source.find(
    "class GenerateSpeechResponse"
)

updated_end = updated_source.find(
    "class GeneratedAudioDeleteResponse",
    updated_start,
)

updated_block = updated_source[
    updated_start:updated_end
]

required_values = [
    '"cosyvoice"',
    '"indicf5"',
    '"hybrid"',
]

for value in required_values:
    if value not in updated_block:
        raise RuntimeError(
            f"Missing engine response value: {value}"
        )

print(
    "Milestone 10.6.7D hybrid response "
    "schema: APPLIED"
)
