from __future__ import annotations

import re
import shutil
import sqlite3
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]

MODELS_PATH = (
    BACKEND_ROOT
    / "app"
    / "database"
    / "models.py"
)

SCHEMAS_PATH = (
    BACKEND_ROOT
    / "app"
    / "database"
    / "schemas.py"
)

SPEECH_PATH = (
    BACKEND_ROOT
    / "app"
    / "api"
    / "speech.py"
)

TTS_PATH = (
    BACKEND_ROOT
    / "app"
    / "services"
    / "tts_service.py"
)

DATABASE_PATH = (
    BACKEND_ROOT
    / "voice.db"
)


ALLOWED_STYLES = [
    "neutral",
    "professional",
    "energetic",
    "calm",
    "storytelling",
]


def read_source(
    path: Path,
) -> str:
    return path.read_text(
        encoding="utf-8-sig",
    )


def write_source(
    path: Path,
    source: str,
) -> None:
    path.write_text(
        source,
        encoding="utf-8",
    )


def replace_once(
    source: str,
    old: str,
    new: str,
    label: str,
) -> str:
    occurrence_count = source.count(old)

    if occurrence_count != 1:
        raise RuntimeError(
            f"{label}: expected exactly one occurrence, "
            f"found {occurrence_count}."
        )

    return source.replace(
        old,
        new,
        1,
    )


# ============================================================
# Schema contract
# ============================================================

schemas_source = read_source(
    SCHEMAS_PATH
)

if "VoiceStyle = Literal[" not in schemas_source:
    voice_style_block = '''VoiceStyle = Literal[
    "neutral",
    "professional",
    "energetic",
    "calm",
    "storytelling",
]


'''

    schemas_source = replace_once(
        schemas_source,
        "class GenerateSpeechRequest(BaseModel):",
        (
            voice_style_block
            + "class GenerateSpeechRequest(BaseModel):"
        ),
        "Insert VoiceStyle alias",
    )

request_start = schemas_source.find(
    "class GenerateSpeechRequest"
)

request_end = schemas_source.find(
    "class SpeechRequest",
    request_start,
)

if request_start < 0 or request_end < 0:
    raise RuntimeError(
        "GenerateSpeechRequest class boundaries "
        "were not found."
    )

request_block = schemas_source[
    request_start:request_end
]

if "    style:" not in request_block:
    style_request_field = '''    style: VoiceStyle = Field(
        default="neutral",
        description="Requested voice delivery style.",
    )

'''

    engine_marker = "    engine: Literal["

    if engine_marker not in request_block:
        raise RuntimeError(
            "GenerateSpeechRequest engine field "
            "was not found."
        )

    request_block = request_block.replace(
        engine_marker,
        style_request_field + engine_marker,
        1,
    )

    schemas_source = (
        schemas_source[:request_start]
        + request_block
        + schemas_source[request_end:]
    )

history_start = schemas_source.find(
    "class GeneratedAudioResponse"
)

history_end = schemas_source.find(
    "class GenerateSpeechResponse",
    history_start,
)

if history_start < 0 or history_end < 0:
    raise RuntimeError(
        "GeneratedAudioResponse class boundaries "
        "were not found."
    )

history_block = schemas_source[
    history_start:history_end
]

if "    style:" not in history_block:
    history_block = replace_once(
        history_block,
        "    bass: float\n",
        (
            "    bass: float\n"
            '    style: VoiceStyle = "neutral"\n'
        ),
        "Insert history style field",
    )

    schemas_source = (
        schemas_source[:history_start]
        + history_block
        + schemas_source[history_end:]
    )

write_source(
    SCHEMAS_PATH,
    schemas_source,
)


# ============================================================
# SQLAlchemy model
# ============================================================

models_source = read_source(
    MODELS_PATH
)

generated_start = models_source.find(
    "class GeneratedAudio"
)

if generated_start < 0:
    raise RuntimeError(
        "GeneratedAudio model was not found."
    )

generated_block = models_source[
    generated_start:
]

if "    style = Column(" not in generated_block:
    created_marker = (
        "    created_at = Column("
        "DateTime, default=datetime.utcnow)"
    )

    style_column = '''    style = Column(
        String,
        nullable=False,
        default="neutral",
        server_default="neutral",
    )

'''

    if created_marker not in generated_block:
        raise RuntimeError(
            "GeneratedAudio created_at column "
            "was not found."
        )

    generated_block = generated_block.replace(
        created_marker,
        style_column + created_marker,
        1,
    )

    models_source = (
        models_source[:generated_start]
        + generated_block
    )

write_source(
    MODELS_PATH,
    models_source,
)


# ============================================================
# Speech API
# ============================================================

speech_source = read_source(
    SPEECH_PATH
)

serialize_start = speech_source.find(
    "def serialize_generation"
)

serialize_end = speech_source.find(
    "# ============================================================",
    serialize_start,
)

if serialize_start < 0 or serialize_end < 0:
    raise RuntimeError(
        "serialize_generation block "
        "was not found."
    )

serialize_block = speech_source[
    serialize_start:serialize_end
]

if '"style": generation.style' not in serialize_block:
    serialize_block = replace_once(
        serialize_block,
        '        "bass": generation.bass,\n',
        (
            '        "bass": generation.bass,\n'
            '        "style": generation.style,\n'
        ),
        "Serialize generation style",
    )

    speech_source = (
        speech_source[:serialize_start]
        + serialize_block
        + speech_source[serialize_end:]
    )

if "            style=request.style," not in speech_source:
    speech_source = replace_once(
        speech_source,
        "            bass=request.bass,\n"
        "            requested_engine=request.engine,\n",
        (
            "            bass=request.bass,\n"
            "            style=request.style,\n"
            "            requested_engine=request.engine,\n"
        ),
        "Pass API style to TTS service",
    )

write_source(
    SPEECH_PATH,
    speech_source,
)


# ============================================================
# TTS service
# ============================================================

tts_source = read_source(
    TTS_PATH
)

if "    ALLOWED_STYLES = {" not in tts_source:
    style_constant = '''class TTSService:

    ALLOWED_STYLES = {
        "neutral",
        "professional",
        "energetic",
        "calm",
        "storytelling",
    }
'''

    tts_source = replace_once(
        tts_source,
        "class TTSService:\n",
        style_constant,
        "Insert TTS style constants",
    )

generation_start = tts_source.find(
    "    def generate_speech("
)

if generation_start < 0:
    raise RuntimeError(
        "TTSService.generate_speech was not found."
    )

generation_source = tts_source[
    generation_start:
]

if "        style: str = \"neutral\"," not in generation_source:
    generation_source = replace_once(
        generation_source,
        (
            "        bass: float = 0.0,\n"
            "        requested_engine: str = \"auto\",\n"
        ),
        (
            "        bass: float = 0.0,\n"
            "        style: str = \"neutral\",\n"
            "        requested_engine: str = \"auto\",\n"
        ),
        "Add TTS style parameter",
    )

if "        clean_style = (" not in generation_source:
    clean_text_marker = (
        "        if not clean_text:\n"
    )

    clean_style_block = '''        clean_style = (
            style
            .strip()
            .lower()
        )

'''

    if clean_text_marker not in generation_source:
        raise RuntimeError(
            "TTS clean-text validation marker "
            "was not found."
        )

    generation_source = generation_source.replace(
        clean_text_marker,
        clean_style_block + clean_text_marker,
        1,
    )

if "clean_style not in self.ALLOWED_STYLES" not in generation_source:
    controls_marker = (
        "        self.validate_controls(\n"
    )

    style_validation = '''        if clean_style not in self.ALLOWED_STYLES:
            allowed_styles = ", ".join(
                sorted(self.ALLOWED_STYLES)
            )

            raise ValueError(
                "Style must be one of: "
                f"{allowed_styles}."
            )

'''

    if controls_marker not in generation_source:
        raise RuntimeError(
            "TTS control-validation marker "
            "was not found."
        )

    generation_source = generation_source.replace(
        controls_marker,
        style_validation + controls_marker,
        1,
    )

if 'print(f"Style           : {clean_style}")' not in generation_source:
    bass_print_pattern = re.compile(
        r'(?P<indent>\s*)print\(f"Bass\s*: \{bass\}"\)'
    )

    generation_source, replacement_count = (
        bass_print_pattern.subn(
            lambda match: (
                match.group(0)
                + "\n"
                + match.group("indent")
                + 'print(f"Style           : {clean_style}")'
            ),
            generation_source,
            count=1,
        )
    )

    if replacement_count != 1:
        print(
            "Style logging marker was not found; "
            "continuing without an additional log line."
        )

if "                style=clean_style," not in generation_source:
    constructor_marker = (
        "                bass=bass,\n"
        "                engine_requested=("
    )

    if constructor_marker not in generation_source:
        raise RuntimeError(
            "GeneratedAudio constructor marker "
            "was not found."
        )

    generation_source = generation_source.replace(
        constructor_marker,
        (
            "                bass=bass,\n"
            "                style=clean_style,\n"
            "                engine_requested=("
        ),
        1,
    )

if '                "style": clean_style,' not in generation_source:
    result_marker = (
        '                "bass": bass,\n'
        '                "created_at": created_at,\n'
    )

    if result_marker not in generation_source:
        raise RuntimeError(
            "TTS result dictionary marker "
            "was not found."
        )

    generation_source = generation_source.replace(
        result_marker,
        (
            '                "bass": bass,\n'
            '                "style": clean_style,\n'
            '                "created_at": created_at,\n'
        ),
        1,
    )

tts_source = (
    tts_source[:generation_start]
    + generation_source
)

write_source(
    TTS_PATH,
    tts_source,
)


# ============================================================
# SQLite migration
# ============================================================

if not DATABASE_PATH.exists():
    raise FileNotFoundError(
        f"Database not found: {DATABASE_PATH}"
    )

connection = sqlite3.connect(
    DATABASE_PATH
)

try:
    connection.execute(
        "BEGIN IMMEDIATE"
    )

    row_count_before = connection.execute(
        "SELECT COUNT(*) FROM generated_audio"
    ).fetchone()[0]

    columns_before = connection.execute(
        "PRAGMA table_info(generated_audio)"
    ).fetchall()

    column_names_before = {
        column[1]
        for column in columns_before
    }

    if "style" not in column_names_before:
        connection.execute(
            """
            ALTER TABLE generated_audio
            ADD COLUMN style VARCHAR
            NOT NULL
            DEFAULT 'neutral'
            """
        )

    connection.execute(
        """
        UPDATE generated_audio
        SET style = 'neutral'
        WHERE style IS NULL
           OR TRIM(style) = ''
        """
    )

    row_count_after = connection.execute(
        "SELECT COUNT(*) FROM generated_audio"
    ).fetchone()[0]

    if row_count_after != row_count_before:
        raise RuntimeError(
            "Generated-audio row count changed "
            "during style migration."
        )

    invalid_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM generated_audio
        WHERE style IS NULL
           OR TRIM(style) = ''
        """
    ).fetchone()[0]

    if invalid_count != 0:
        raise RuntimeError(
            "Style migration left invalid rows."
        )

    connection.commit()

finally:
    connection.close()


print(
    "Milestone 10.7B application style wiring: APPLIED"
)

print(
    "Milestone 10.7B database style migration: APPLIED"
)
