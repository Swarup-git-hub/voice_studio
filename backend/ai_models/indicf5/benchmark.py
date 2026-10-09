from __future__ import annotations

import gc
import json
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

import huggingface_hub
import numpy as np
import soundfile as sf
import torch
import transformers
from transformers import AutoModel


PROJECT_ROOT = Path(
    r"D:\swarup\swarup.vscode\ai_voice_studio(my)"
).resolve()

BACKEND_ROOT = PROJECT_ROOT / "backend"

REFERENCE_AUDIO = (
    BACKEND_ROOT
    / "app"
    / "voices"
    / "reference_a676a66d93a748508262ee445cdd6138.wav"
)

OUTPUT_FOLDER = (
    BACKEND_ROOT
    / "ai_models"
    / "indicf5"
    / "outputs"
)

REPORT_PATH = OUTPUT_FOLDER / "benchmark_results.json"

MODEL_ID = "ai4bharat/IndicF5"

REFERENCE_TRANSCRIPT = (
    "Hello everyone. This is my synchronized reference voice. "
    "I am speaking clearly, naturally, and with steady energy. "
    "So the model can learn my voice correctly."
)

BENCHMARKS = {
    "english": (
        "When the reference audio and transcript match exactly, "
        "the generated voice should remain stable, clear, and consistent."
    ),
    "telugu": (
        "బ్రౌజర్‌లో యూ ఆర్ ఎల్ టైప్ చేసి ఎంటర్ నొక్కితే, "
        "తర్వాత అసలు ఏం జరుగుతుంది?"
    ),
    "mixed": (
        "Browser లో U R L type చేసి Enter నొక్కితే, "
        "next exactly ఏం జరుగుతుంది?"
    ),
}


def synchronize_cuda() -> None:
    if torch.cuda.is_available():
        torch.cuda.synchronize()


def current_vram_mb() -> float | None:
    if not torch.cuda.is_available():
        return None

    return round(
        torch.cuda.memory_allocated() / (1024 ** 2),
        2,
    )


def peak_vram_mb() -> float | None:
    if not torch.cuda.is_available():
        return None

    return round(
        torch.cuda.max_memory_allocated() / (1024 ** 2),
        2,
    )


def convert_to_numpy(audio: Any) -> np.ndarray:
    if isinstance(audio, torch.Tensor):
        audio = (
            audio
            .detach()
            .cpu()
            .numpy()
        )

    audio_array = np.asarray(audio)

    audio_array = np.squeeze(
        audio_array
    )

    if audio_array.ndim != 1:
        raise ValueError(
            "IndicF5 returned an unexpected audio "
            f"shape: {audio_array.shape}"
        )

    if audio_array.size == 0:
        raise ValueError(
            "IndicF5 returned empty audio."
        )

    if audio_array.dtype == np.int16:
        audio_array = (
            audio_array.astype(np.float32)
            / 32768.0
        )
    else:
        audio_array = audio_array.astype(
            np.float32
        )

    audio_array = np.nan_to_num(
        audio_array,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    peak = float(
        np.max(
            np.abs(audio_array)
        )
    )

    if peak <= 0:
        raise ValueError(
            "IndicF5 returned silent audio."
        )

    if peak > 1.0:
        audio_array = audio_array / peak

    return audio_array


def save_audio(
    audio: Any,
    output_path: Path,
) -> dict[str, Any]:
    audio_array = convert_to_numpy(
        audio
    )

    sf.write(
        str(output_path),
        audio_array,
        samplerate=24000,
        subtype="PCM_16",
    )

    if not output_path.exists():
        raise RuntimeError(
            f"Output WAV was not created: {output_path}"
        )

    if output_path.stat().st_size <= 0:
        raise RuntimeError(
            f"Output WAV is empty: {output_path}"
        )

    audio_info = sf.info(
        str(output_path)
    )

    return {
        "path": str(output_path),
        "filename": output_path.name,
        "size_bytes": output_path.stat().st_size,
        "sample_rate": audio_info.samplerate,
        "channels": audio_info.channels,
        "duration_seconds": round(
            audio_info.duration,
            3,
        ),
        "subtype": audio_info.subtype,
    }


def write_report(
    report: dict[str, Any],
) -> None:
    REPORT_PATH.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def main() -> int:
    OUTPUT_FOLDER.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not REFERENCE_AUDIO.exists():
        raise FileNotFoundError(
            "Reference audio was not found:\n"
            f"{REFERENCE_AUDIO}"
        )

    if REFERENCE_AUDIO.stat().st_size <= 0:
        raise ValueError(
            "Reference audio is empty."
        )

    report: dict[str, Any] = {
        "started_at": datetime.now().isoformat(),
        "model_id": MODEL_ID,
        "reference_audio": str(REFERENCE_AUDIO),
        "reference_transcript": REFERENCE_TRANSCRIPT,
        "environment": {
            "python": sys.version,
            "torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "cuda_available": torch.cuda.is_available(),
            "gpu": (
                torch.cuda.get_device_name(0)
                if torch.cuda.is_available()
                else None
            ),
            "transformers": transformers.__version__,
            "huggingface_hub": huggingface_hub.__version__,
        },
        "model_load": {},
        "benchmarks": {},
    }

    print("=" * 80)
    print("INDICF5 CONTROLLED BENCHMARK")
    print("=" * 80)

    print("Model     :", MODEL_ID)
    print("Reference :", REFERENCE_AUDIO)
    print("CUDA      :", torch.cuda.is_available())

    if torch.cuda.is_available():
        print(
            "GPU       :",
            torch.cuda.get_device_name(0),
        )

        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()

    gc.collect()

    print("\nLoading IndicF5...")
    print(
        "The first run may download and cache "
        "the model files."
    )

    synchronize_cuda()
    load_started = time.perf_counter()

    try:
        model = AutoModel.from_pretrained(
            MODEL_ID,
            trust_remote_code=True,
        )
    except Exception as error:
        report["model_load"] = {
            "status": "failed",
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }

        write_report(report)

        print("\nMODEL LOAD FAILED")
        print(type(error).__name__)
        print(str(error))
        print("\nA detailed traceback was saved to:")
        print(REPORT_PATH)

        return 1

    synchronize_cuda()

    model_load_seconds = round(
        time.perf_counter() - load_started,
        2,
    )

    report["model_load"] = {
        "status": "passed",
        "seconds": model_load_seconds,
        "current_vram_mb": current_vram_mb(),
        "peak_vram_mb": peak_vram_mb(),
    }

    write_report(report)

    print(
        f"Model loaded in {model_load_seconds} seconds."
    )

    print(
        "Current VRAM:",
        current_vram_mb(),
        "MB",
    )

    for benchmark_name, target_text in (
        BENCHMARKS.items()
    ):
        print("\n" + "-" * 80)
        print("Benchmark:", benchmark_name)
        print("Text     :", target_text)

        output_path = (
            OUTPUT_FOLDER
            / f"indicf5_{benchmark_name}.wav"
        )

        if output_path.exists():
            output_path.unlink()

        synchronize_cuda()

        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()

        generation_started = (
            time.perf_counter()
        )

        try:
            audio = model(
                target_text,
                ref_audio_path=str(
                    REFERENCE_AUDIO
                ),
                ref_text=REFERENCE_TRANSCRIPT,
            )

            synchronize_cuda()

            generation_seconds = round(
                time.perf_counter()
                - generation_started,
                2,
            )

            audio_details = save_audio(
                audio=audio,
                output_path=output_path,
            )

            result = {
                "status": "passed",
                "text": target_text,
                "generation_seconds": generation_seconds,
                "current_vram_mb": current_vram_mb(),
                "peak_vram_mb": peak_vram_mb(),
                "audio": audio_details,
            }

            report["benchmarks"][
                benchmark_name
            ] = result

            print(
                "Generation time:",
                generation_seconds,
                "seconds",
            )

            print(
                "Output:",
                output_path,
            )

            print(
                "Duration:",
                audio_details["duration_seconds"],
                "seconds",
            )

            print(
                "Sample rate:",
                audio_details["sample_rate"],
            )

            print(
                "Channels:",
                audio_details["channels"],
            )

            print(
                "Peak VRAM:",
                peak_vram_mb(),
                "MB",
            )

        except Exception as error:
            report["benchmarks"][
                benchmark_name
            ] = {
                "status": "failed",
                "text": target_text,
                "error_type": type(error).__name__,
                "error": str(error),
                "traceback": traceback.format_exc(),
            }

            print(
                "BENCHMARK FAILED:",
                benchmark_name,
            )

            print(type(error).__name__)
            print(str(error))

        finally:
            write_report(report)

            if "audio" in locals():
                del audio

            gc.collect()

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    report["completed_at"] = (
        datetime.now().isoformat()
    )

    write_report(report)

    print("\n" + "=" * 80)
    print("INDICF5 BENCHMARK COMPLETE")
    print("=" * 80)
    print("Report:", REPORT_PATH)

    passed_count = sum(
        1
        for result in report["benchmarks"].values()
        if result.get("status") == "passed"
    )

    print(
        "Passed:",
        passed_count,
        "of",
        len(BENCHMARKS),
    )

    return (
        0
        if passed_count == len(BENCHMARKS)
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
