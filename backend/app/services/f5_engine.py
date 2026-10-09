from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests


class IndicF5UnavailableError(ConnectionError):
    """Raised when the IndicF5 HTTP service cannot be used."""


class IndicF5GenerationError(RuntimeError):
    """Raised when IndicF5 fails to create or return valid audio."""


class IndicF5Engine:
    """
    HTTP client for the persistent IndicF5 service on port 8002.

    The neural model remains inside the dedicated indicf5_env
    process. The main FastAPI backend communicates with it only
    through HTTP.
    """

    ALLOWED_LANGUAGES = {
        "auto",
        "english",
        "telugu",
        "mixed",
    }

    MAX_TEXT_CHARACTERS = 1500
    MAX_TRANSCRIPT_CHARACTERS = 5000

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8002",
    ) -> None:
        self.base_url = base_url.rstrip("/")

    # ========================================================
    # Response helpers
    # ========================================================

    @staticmethod
    def _response_detail(
        response: requests.Response,
    ) -> str:
        try:
            payload = response.json()
        except ValueError:
            return (
                response.text.strip()
                or "No response details were returned."
            )

        if isinstance(payload, dict):
            detail = payload.get("detail")

            if detail:
                return str(detail)

        return str(payload)

    # ========================================================
    # Health check
    # ========================================================

    def load(self) -> dict[str, Any]:
        """
        Verify that the standalone service and GPU model are ready.

        The method name is kept as load() for compatibility with the
        existing engine style. It does not load the neural model into
        the main backend process.
        """

        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=(3, 10),
            )

        except requests.ConnectionError as error:
            raise IndicF5UnavailableError(
                "Could not connect to IndicF5 at "
                "http://127.0.0.1:8002."
            ) from error

        except requests.Timeout as error:
            raise IndicF5UnavailableError(
                "IndicF5 health check timed out."
            ) from error

        except requests.RequestException as error:
            raise IndicF5UnavailableError(
                "IndicF5 health check failed."
            ) from error

        if response.status_code != 200:
            raise IndicF5UnavailableError(
                "IndicF5 health check failed. "
                f"Status: {response.status_code}. "
                f"Detail: {self._response_detail(response)}"
            )

        try:
            health_data = response.json()
        except ValueError as error:
            raise IndicF5UnavailableError(
                "IndicF5 returned invalid health-check JSON."
            ) from error

        if not health_data.get("model_loaded"):
            raise IndicF5UnavailableError(
                "IndicF5 is running, but its model is not loaded."
            )

        if health_data.get("status") != "healthy":
            raise IndicF5UnavailableError(
                "IndicF5 did not report a healthy status."
            )

        return health_data

    # ========================================================
    # Generation
    # ========================================================

    def generate(
        self,
        reference_audio: str,
        prompt_text: str,
        text: str,
        output_path: str,
        speed: float = 1.0,
        language: str = "auto",
    ) -> dict[str, Any]:
        """
        Generate speech through the service and download the WAV.

        IndicF5 currently generates at its native speaking speed.
        The requested speed is returned as metadata so the shared
        final-processing layer can apply it later.
        """

        reference_path = Path(
            reference_audio
        ).expanduser().resolve()

        destination_path = Path(
            output_path
        ).expanduser().resolve()

        clean_text = text.strip()
        clean_prompt_text = prompt_text.strip()
        clean_language = language.strip().lower()

        if not reference_path.exists():
            raise FileNotFoundError(
                "IndicF5 reference audio was not found:\n"
                f"{reference_path}"
            )

        if not reference_path.is_file():
            raise ValueError(
                "IndicF5 reference audio is not a file."
            )

        if reference_path.suffix.lower() != ".wav":
            raise ValueError(
                "IndicF5 reference audio must be a WAV file."
            )

        if not clean_text:
            raise ValueError(
                "IndicF5 synthesis text cannot be empty."
            )

        if len(clean_text) > self.MAX_TEXT_CHARACTERS:
            raise ValueError(
                "IndicF5 synthesis text cannot exceed "
                f"{self.MAX_TEXT_CHARACTERS} characters."
            )

        if not clean_prompt_text:
            raise ValueError(
                "IndicF5 reference transcript cannot be empty."
            )

        if (
            len(clean_prompt_text)
            > self.MAX_TRANSCRIPT_CHARACTERS
        ):
            raise ValueError(
                "IndicF5 reference transcript cannot exceed "
                f"{self.MAX_TRANSCRIPT_CHARACTERS} characters."
            )

        if clean_language not in self.ALLOWED_LANGUAGES:
            raise ValueError(
                "IndicF5 language must be one of: "
                "auto, english, telugu, mixed."
            )

        if not 0.5 <= speed <= 2.0:
            raise ValueError(
                "Speed must be between 0.5 and 2.0."
            )

        destination_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload = {
            "text": clean_text,
            "reference_audio": str(reference_path),
            "reference_transcript": clean_prompt_text,
            "language": clean_language,
        }

        try:
            response = requests.post(
                f"{self.base_url}/generate",
                json=payload,
                timeout=(10, 900),
            )

        except requests.ConnectionError as error:
            raise IndicF5UnavailableError(
                "Could not connect to IndicF5 at "
                "http://127.0.0.1:8002."
            ) from error

        except requests.Timeout as error:
            raise IndicF5UnavailableError(
                "IndicF5 generation timed out."
            ) from error

        except requests.RequestException as error:
            raise IndicF5GenerationError(
                "IndicF5 generation request failed."
            ) from error

        detail = self._response_detail(response)

        if response.status_code == 400:
            raise ValueError(
                f"IndicF5 rejected the request: {detail}"
            )

        if response.status_code == 503:
            raise IndicF5UnavailableError(
                f"IndicF5 is unavailable: {detail}"
            )

        if response.status_code != 200:
            raise IndicF5GenerationError(
                "IndicF5 generation failed. "
                f"Status: {response.status_code}. "
                f"Detail: {detail}"
            )

        try:
            generation_data = response.json()
        except ValueError as error:
            raise IndicF5GenerationError(
                "IndicF5 returned invalid generation JSON."
            ) from error

        output_url = generation_data.get("output_url")

        if not isinstance(output_url, str) or not output_url:
            raise IndicF5GenerationError(
                "IndicF5 response did not contain output_url."
            )

        download_url = urljoin(
            f"{self.base_url}/",
            output_url.lstrip("/"),
        )

        try:
            audio_response = requests.get(
                download_url,
                timeout=(10, 120),
            )

        except requests.ConnectionError as error:
            raise IndicF5UnavailableError(
                "IndicF5 generated the audio, but the backend "
                "could not connect to its download endpoint."
            ) from error

        except requests.Timeout as error:
            raise IndicF5GenerationError(
                "IndicF5 output download timed out."
            ) from error

        except requests.RequestException as error:
            raise IndicF5GenerationError(
                "IndicF5 output download failed."
            ) from error

        if audio_response.status_code != 200:
            raise IndicF5GenerationError(
                "IndicF5 output download failed. "
                f"Status: {audio_response.status_code}. "
                f"Detail: {self._response_detail(audio_response)}"
            )

        if not audio_response.content:
            raise IndicF5GenerationError(
                "IndicF5 returned an empty WAV download."
            )

        try:
            destination_path.write_bytes(
                audio_response.content
            )

            if not destination_path.exists():
                raise IndicF5GenerationError(
                    "The IndicF5 WAV was not saved."
                )

            if destination_path.stat().st_size <= 0:
                raise IndicF5GenerationError(
                    "The saved IndicF5 WAV is empty."
                )

        except Exception:
            destination_path.unlink(
                missing_ok=True
            )
            raise

        return {
            "engine": "indicf5",
            "device": generation_data.get("device"),
            "language": generation_data.get(
                "language",
                clean_language,
            ),
            "output_path": str(destination_path),
            "server_output_file": generation_data.get(
                "output_file"
            ),
            "server_output_path": generation_data.get(
                "output_path"
            ),
            "generation_seconds": generation_data.get(
                "generation_seconds"
            ),
            "audio_duration_seconds": generation_data.get(
                "audio_duration_seconds"
            ),
            "real_time_factor": generation_data.get(
                "real_time_factor"
            ),
            "sample_rate": generation_data.get(
                "sample_rate"
            ),
            "channels": generation_data.get(
                "channels"
            ),
            "peak_cuda_mb": generation_data.get(
                "peak_cuda_mb"
            ),
            "speed_requested": speed,
            "speed_applied_by_engine": False,
        }


# Backward-compatible alias for any existing imports.
F5Engine = IndicF5Engine

engine = IndicF5Engine()
