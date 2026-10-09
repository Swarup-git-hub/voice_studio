from __future__ import annotations

import gc
import time
from collections import Counter
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
import soundfile as sf
import torch
from transformers import AutoModel

from .config import (
    DEVICE,
    MODEL_ID,
    OUTPUT_DIRECTORY,
    SAMPLE_RATE,
    VOICES_DIRECTORY,
)


class IndicF5Engine:
    def __init__(self) -> None:
        self.model: Any | None = None
        self.device = torch.device(DEVICE)

        self.load_seconds: float | None = None
        self.total_parameters = 0
        self.cpu_parameters = 0
        self.cuda_parameters = 0

    @property
    def loaded(self) -> bool:
        return self.model is not None

    @staticmethod
    def _bytes_to_mb(
        value: int,
    ) -> float:
        return round(
            value / (1024**2),
            2,
        )

    @staticmethod
    def _synchronize_cuda() -> None:
        if torch.cuda.is_available():
            torch.cuda.synchronize()

    def _collect_parameter_devices(
        self,
    ) -> None:
        if self.model is None:
            self.total_parameters = 0
            self.cpu_parameters = 0
            self.cuda_parameters = 0
            return

        parameter_counts: Counter[str] = Counter()

        total_parameters = 0

        for parameter in self.model.parameters():
            count = parameter.numel()
            device_name = str(parameter.device)

            total_parameters += count

            parameter_counts[device_name] += count

        self.total_parameters = total_parameters

        self.cpu_parameters = parameter_counts.get(
            "cpu",
            0,
        )

        self.cuda_parameters = sum(
            count
            for device_name, count in parameter_counts.items()
            if device_name.startswith("cuda")
        )

    def load(self) -> None:
        if self.loaded:
            return

        if self.device.type == "cuda" and not torch.cuda.is_available():
            raise RuntimeError(
                "IndicF5 is configured for CUDA, " "but CUDA is unavailable."
            )

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()

        gc.collect()

        started = time.perf_counter()

        model = AutoModel.from_pretrained(
            MODEL_ID,
            trust_remote_code=True,
        )

        model = model.to(self.device)

        model.eval()

        self._synchronize_cuda()

        self.model = model

        self.load_seconds = round(
            time.perf_counter() - started,
            2,
        )

        self._collect_parameter_devices()

        if self.device.type == "cuda" and self.cuda_parameters <= 0:
            self.shutdown()

            raise RuntimeError(
                "IndicF5 loaded, but no CUDA " "parameters were detected."
            )

    def shutdown(self) -> None:
        model = self.model
        self.model = None

        if model is not None:
            try:
                model.to("cpu")
            except Exception:
                pass

            del model

        gc.collect()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        self._collect_parameter_devices()

    @staticmethod
    def _normalize_audio(
        generated_audio: Any,
    ) -> np.ndarray:
        if isinstance(
            generated_audio,
            torch.Tensor,
        ):
            generated_audio = generated_audio.detach().cpu().numpy()

        audio = np.asarray(generated_audio)

        audio = np.squeeze(audio)

        if audio.ndim != 1:
            raise ValueError("Unexpected generated-audio " f"shape: {audio.shape}")

        if audio.size == 0:
            raise ValueError("Generated audio is empty.")

        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0
        else:
            audio = audio.astype(np.float32)

        audio = np.nan_to_num(
            audio,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )

        if not np.isfinite(audio).all():
            raise ValueError("Generated audio contains " "non-finite values.")

        peak = float(np.max(np.abs(audio)))

        if peak <= 0:
            raise ValueError("Generated audio is silent.")

        if peak > 1.0:
            audio = audio / peak

        return audio

    @staticmethod
    def _resolve_reference(
        reference_audio: str,
    ) -> Path:
        candidate = Path(reference_audio).expanduser()

        if not candidate.is_absolute():
            candidate = VOICES_DIRECTORY / candidate

        candidate = candidate.resolve()
        voices_root = VOICES_DIRECTORY.resolve()

        try:
            candidate.relative_to(voices_root)
        except ValueError as error:
            raise ValueError(
                "Reference audio must be located " "inside backend/app/voices."
            ) from error

        if not candidate.exists():
            raise FileNotFoundError("Reference audio was not found: " f"{candidate}")

        if not candidate.is_file():
            raise ValueError("Reference audio is not a file.")

        if candidate.suffix.lower() != ".wav":
            raise ValueError("IndicF5 reference audio must " "be a WAV file.")

        return candidate

    def generate(
        self,
        *,
        text: str,
        reference_audio: str,
        reference_transcript: str,
    ) -> dict[str, Any]:
        if self.model is None:
            raise RuntimeError("IndicF5 is not loaded.")

        clean_text = text.strip()
        clean_transcript = reference_transcript.strip()

        if not clean_text:
            raise ValueError("Target text cannot be empty.")

        if not clean_transcript:
            raise ValueError("Reference transcript cannot " "be empty.")

        reference_path = self._resolve_reference(reference_audio)

        output_name = f"indicf5_{uuid4().hex}.wav"

        output_path = OUTPUT_DIRECTORY / output_name

        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()

        self._synchronize_cuda()

        started = time.perf_counter()

        with torch.inference_mode():
            generated_audio = self.model(
                clean_text,
                ref_audio_path=str(reference_path),
                ref_text=clean_transcript,
            )

        self._synchronize_cuda()

        generation_seconds = round(
            time.perf_counter() - started,
            3,
        )

        audio = self._normalize_audio(generated_audio)

        sf.write(
            str(output_path),
            audio,
            samplerate=SAMPLE_RATE,
            subtype="PCM_16",
        )

        if not output_path.exists():
            raise RuntimeError("Generated output file was " "not created.")

        if output_path.stat().st_size <= 0:
            output_path.unlink(missing_ok=True)

            raise RuntimeError("Generated output file is empty.")

        info = sf.info(str(output_path))

        audio_duration = round(
            info.duration,
            3,
        )

        real_time_factor = round(
            generation_seconds / audio_duration,
            3,
        )

        peak_cuda_mb = 0.0

        if torch.cuda.is_available():
            peak_cuda_mb = self._bytes_to_mb(torch.cuda.max_memory_allocated())

        return {
            "output_file": output_name,
            "output_path": str(output_path),
            "generation_seconds": (generation_seconds),
            "audio_duration_seconds": (audio_duration),
            "real_time_factor": (real_time_factor),
            "sample_rate": (info.samplerate),
            "channels": (info.channels),
            "peak_cuda_mb": (peak_cuda_mb),
        }

    def health_data(
        self,
    ) -> dict[str, Any]:
        gpu_name: str | None = None

        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)

        allocated_mb = 0.0
        reserved_mb = 0.0

        if torch.cuda.is_available():
            allocated_mb = self._bytes_to_mb(torch.cuda.memory_allocated())

            reserved_mb = self._bytes_to_mb(torch.cuda.memory_reserved())

        return {
            "model_loaded": self.loaded,
            "device": str(self.device),
            "cuda_available": (torch.cuda.is_available()),
            "gpu_name": gpu_name,
            "cuda_allocated_mb": (allocated_mb),
            "cuda_reserved_mb": (reserved_mb),
        }