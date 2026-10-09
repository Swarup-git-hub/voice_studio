from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


LanguageType = Literal[
    "auto",
    "english",
    "telugu",
    "mixed",
]


class GenerateRequest(BaseModel):
    text: str = Field(
        min_length=1,
        max_length=1500,
    )

    reference_audio: str = Field(
        min_length=1,
    )

    reference_transcript: str = Field(
        min_length=1,
        max_length=5000,
    )

    language: LanguageType = "auto"


class GenerateResponse(BaseModel):
    status: str
    engine: str
    device: str
    language: LanguageType

    output_file: str
    output_path: str
    output_url: str

    generation_seconds: float
    audio_duration_seconds: float
    real_time_factor: float

    sample_rate: int
    channels: int
    peak_cuda_mb: float


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    model_id: str
    model_loaded: bool
    device: str
    cuda_available: bool
    gpu_name: str | None
    cuda_allocated_mb: float
    cuda_reserved_mb: float


class ModelStatusResponse(BaseModel):
    model_id: str
    loaded: bool
    device: str
    total_parameters: int
    cpu_parameters: int
    cuda_parameters: int
    load_seconds: float | None
