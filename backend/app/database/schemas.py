from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator

# ============================================================
# Voice Schemas
# ============================================================


class VoiceResponse(BaseModel):
    id: int
    voice_name: str
    language: str
    wav_filename: str
    duration: float
    sample_rate: int
    transcript: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class VoiceUpdate(BaseModel):
    voice_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    language: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    transcript: str | None = Field(
        default=None,
        min_length=1,
        max_length=10000,
    )

    @model_validator(mode="after")
    def validate_update_fields(self):

        if (
            self.voice_name is None
            and self.language is None
            and self.transcript is None
        ):
            raise ValueError(
                "Provide at least one field: " "voice_name, language, or transcript."
            )

        return self


class VoiceDeleteResponse(BaseModel):
    status: str
    voice_id: int
    voice_name: str
    generated_audio_records_deleted: int
    files_deleted: int
    files_not_found: int
    message: str


# ============================================================
# Speech Generation Schemas
# ============================================================


VoiceStyle = Literal[
    "neutral",
    "professional",
    "energetic",
    "calm",
    "storytelling",
]


class GenerateSpeechRequest(BaseModel):
    voice_id: int = Field(
        gt=0,
        description="ID of the saved reference voice.",
    )

    text: str = Field(
        min_length=1,
        max_length=10000,
        description="Text that should be converted into speech.",
    )

    speed: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
    )

    volume: float = Field(
        default=1.0,
        ge=0.1,
        le=3.0,
    )

    bass: float = Field(
        default=0.0,
        ge=-20.0,
        le=20.0,
    )

    style: VoiceStyle = Field(
        default="neutral",
        description="Requested voice delivery style.",
    )

    engine: Literal[
        "auto",
        "cosyvoice",
        "indicf5",
    ] = Field(
        default="auto",
        description=(
            "Speech engine selection. Auto chooses an engine "
            "from the detected language and may use fallback."
        ),
    )

    allow_fallback: bool = Field(
        default=True,
        description=(
            "Allow Auto mode to try the secondary engine when "
            "the primary engine is unavailable or fails."
        ),
    )


class SpeechRequest(GenerateSpeechRequest):
    pass


# ============================================================
# Generated Audio Schemas
# ============================================================


class GeneratedAudioResponse(BaseModel):
    id: int
    voice_id: int
    voice_name: str | None = None
    text: str
    output_filename: str
    speed: float
    volume: float
    bass: float
    style: VoiceStyle = "neutral"
    created_at: datetime
    audio_url: str
    download_url: str

    engine_requested: str = "legacy"
    engine_used: str = "legacy"
    fallback_used: bool = False
    routing_reason: str = "legacy_record"


class GenerateSpeechResponse(GeneratedAudioResponse):
    status: str = "success"

    engine_requested: Literal[
        "auto",
        "cosyvoice",
        "indicf5",
    ]

    engine_used: Literal[
        "cosyvoice",
        "indicf5",
        "hybrid",
    ]

    detected_language: Literal[
        "english",
        "telugu",
        "mixed",
    ]

    fallback_used: bool
    routing_reason: str
    quality_warning: str | None = None


class GeneratedAudioDeleteResponse(BaseModel):
    status: str
    generation_id: int
    database_record_deleted: bool
    audio_file_deleted: bool
    message: str