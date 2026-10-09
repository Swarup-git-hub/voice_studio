from __future__ import annotations

import gc
import json
import sys


# INDICF5_UTF8_CONSOLE_FIX
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(
        encoding="utf-8",
        errors="replace",
    )

if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(
        encoding="utf-8",
        errors="replace",
    )

import time
import traceback
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
import torch
from transformers import AutoModel


PROJECT_ROOT = Path(
    r"D:\swarup\swarup.vscode\ai_voice_studio(my)"
).resolve()

BACKEND_ROOT = PROJECT_ROOT / "backend"

INDICF5_ROOT = (
    BACKEND_ROOT
    / "ai_models"
    / "indicf5"
)

OUTPUT_FOLDER = (
    INDICF5_ROOT
    / "outputs"
)

OUTPUT_FOLDER.mkdir(
    parents=True,
    exist_ok=True,
)

REFERENCE_AUDIO = (
    BACKEND_ROOT
    / "app"
    / "voices"
    / "reference_a676a66d93a748508262ee445cdd6138.wav"
)

REFERENCE_TRANSCRIPT = (
    "Hello everyone. This is my synchronized reference voice. "
    "I am speaking clearly, naturally, and with steady energy. "
    "So the model can learn my voice correctly."
)

MODEL_ID = "ai4bharat/IndicF5"

TARGET_DEVICE = torch.device(
    "cuda:0"
)

REPORT_PATH = (
    OUTPUT_FOLDER
    / "gpu_benchmark_results.json"
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


def bytes_to_mb(value: int) -> float:
    return round(
        value / (1024 ** 2),
        2,
    )


def collect_parameter_devices(
    model: torch.nn.Module,
) -> dict[str, Any]:
    parameter_counts: Counter[str] = Counter()
    tensor_counts: Counter[str] = Counter()

    total_parameters = 0
    meta_parameters = 0

    for parameter in model.parameters():
        device_name = str(
            parameter.device
        )

        count = parameter.numel()

        parameter_counts[
            device_name
        ] += count

        tensor_counts[
            device_name
        ] += 1

        total_parameters += count

        if parameter.is_meta:
            meta_parameters += count

    return {
        "total_parameters": total_parameters,
        "meta_parameters": meta_parameters,
        "parameter_counts": dict(
            parameter_counts
        ),
        "tensor_counts": dict(
            tensor_counts
        ),
    }


def normalize_audio(
    generated_audio: Any,
) -> np.ndarray:
    if isinstance(
        generated_audio,
        torch.Tensor,
    ):
        generated_audio = (
            generated_audio
            .detach()
            .cpu()
            .numpy()
        )

    audio = np.asarray(
        generated_audio
    )

    audio = np.squeeze(
        audio
    )

    if audio.ndim != 1:
        raise ValueError(
            "Unexpected audio shape: "
            f"{audio.shape}"
        )

    if audio.size == 0:
        raise ValueError(
            "Generated audio is empty."
        )

    if audio.dtype == np.int16:
        audio = (
            audio.astype(np.float32)
            / 32768.0
        )
    else:
        audio = audio.astype(
            np.float32
        )

    audio = np.nan_to_num(
        audio,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    peak = float(
        np.max(
            np.abs(audio)
        )
    )

    if peak <= 0:
        raise ValueError(
            "Generated audio is silent."
        )

    if peak > 1.0:
        audio = audio / peak

    return audio


def save_audio(
    generated_audio: Any,
    output_path: Path,
) -> dict[str, Any]:
    audio = normalize_audio(
        generated_audio
    )

    sf.write(
        str(output_path),
        audio,
        samplerate=24000,
        subtype="PCM_16",
    )

    if not output_path.exists():
        raise RuntimeError(
            f"Output was not created: {output_path}"
        )

    if output_path.stat().st_size <= 0:
        raise RuntimeError(
            f"Output is empty: {output_path}"
        )

    info = sf.info(
        str(output_path)
    )

    return {
        "filename": output_path.name,
        "path": str(output_path),
        "size_bytes": output_path.stat().st_size,
        "duration_seconds": round(
            info.duration,
            3,
        ),
        "sample_rate": info.samplerate,
        "channels": info.channels,
        "subtype": info.subtype,
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
    report: dict[str, Any] = {
        "started_at": datetime.now().isoformat(),
        "model_id": MODEL_ID,
        "target_device": str(
            TARGET_DEVICE
        ),
        "reference_audio": str(
            REFERENCE_AUDIO
        ),
        "reference_transcript": (
            REFERENCE_TRANSCRIPT
        ),
        "environment": {
            "python": sys.version,
            "torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "cuda_available": (
                torch.cuda.is_available()
            ),
            "gpu": (
                torch.cuda.get_device_name(0)
                if torch.cuda.is_available()
                else None
            ),
        },
        "model_load": {},
        "gpu_move": {},
        "benchmarks": {},
    }

    print("=" * 80)
    print("INDICF5 COMPLETE GPU BENCHMARK")
    print("=" * 80)

    print("Model :", MODEL_ID)
    print("Device:", TARGET_DEVICE)
    print("CUDA  :", torch.cuda.is_available())

    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is not available."
        )

    print(
        "GPU   :",
        torch.cuda.get_device_name(0),
    )

    if not REFERENCE_AUDIO.exists():
        raise FileNotFoundError(
            f"Reference not found: {REFERENCE_AUDIO}"
        )

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    gc.collect()

    print("\nLoading IndicF5 on CPU...")

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
        raise

    load_seconds = round(
        time.perf_counter()
        - load_started,
        2,
    )

    before_move = collect_parameter_devices(
        model
    )

    report["model_load"] = {
        "status": "passed",
        "seconds": load_seconds,
        "devices": before_move,
    }

    print(
        "Model loaded in:",
        load_seconds,
        "seconds",
    )

    print(
        "Before move:",
        before_move["parameter_counts"],
    )

    print("\nMoving model to cuda:0...")

    move_started = time.perf_counter()

    try:
        model = model.to(
            TARGET_DEVICE
        )

        model.eval()

        synchronize_cuda()

    except Exception as error:
        report["gpu_move"] = {
            "status": "failed",
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }

        write_report(report)
        raise

    move_seconds = round(
        time.perf_counter()
        - move_started,
        2,
    )

    after_move = collect_parameter_devices(
        model
    )

    report["gpu_move"] = {
        "status": "passed",
        "seconds": move_seconds,
        "devices": after_move,
        "allocated_mb": bytes_to_mb(
            torch.cuda.memory_allocated()
        ),
        "reserved_mb": bytes_to_mb(
            torch.cuda.memory_reserved()
        ),
    }

    print(
        "After move:",
        after_move["parameter_counts"],
    )

    print(
        "CUDA allocated:",
        report["gpu_move"]["allocated_mb"],
        "MB",
    )

    cuda_parameters = sum(
        count
        for device_name, count
        in after_move[
            "parameter_counts"
        ].items()
        if device_name.startswith(
            "cuda"
        )
    )

    if cuda_parameters <= 0:
        raise RuntimeError(
            "No CUDA parameters were detected."
        )

    passed_count = 0

    for benchmark_name, target_text in (
        BENCHMARKS.items()
    ):
        print("\n" + "-" * 80)
        print("Benchmark:", benchmark_name)
        print("Text     :", target_text)

        output_path = (
            OUTPUT_FOLDER
            / f"indicf5_gpu_{benchmark_name}.wav"
        )

        if output_path.exists():
            output_path.unlink()

        torch.cuda.reset_peak_memory_stats()

        synchronize_cuda()

        generation_started = (
            time.perf_counter()
        )

        generated_audio: Any | None = None

        try:
            with torch.inference_mode():
                generated_audio = model(
                    target_text,
                    ref_audio_path=str(
                        REFERENCE_AUDIO
                    ),
                    ref_text=(
                        REFERENCE_TRANSCRIPT
                    ),
                )

            synchronize_cuda()

            generation_seconds = round(
                time.perf_counter()
                - generation_started,
                2,
            )

            audio_details = save_audio(
                generated_audio,
                output_path,
            )

            real_time_factor = round(
                generation_seconds
                / audio_details[
                    "duration_seconds"
                ],
                2,
            )

            result = {
                "status": "passed",
                "text": target_text,
                "generation_seconds": (
                    generation_seconds
                ),
                "real_time_factor": (
                    real_time_factor
                ),
                "peak_cuda_mb": bytes_to_mb(
                    torch.cuda.max_memory_allocated()
                ),
                "current_cuda_mb": bytes_to_mb(
                    torch.cuda.memory_allocated()
                ),
                "audio": audio_details,
            }

            report["benchmarks"][
                benchmark_name
            ] = result

            passed_count += 1

            print(
                "Generation time:",
                generation_seconds,
                "seconds",
            )

            print(
                "Audio duration:",
                audio_details[
                    "duration_seconds"
                ],
                "seconds",
            )

            print(
                "Real-time factor:",
                real_time_factor,
            )

            print(
                "Peak CUDA:",
                result["peak_cuda_mb"],
                "MB",
            )

            print(
                "Output:",
                output_path,
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
            if generated_audio is not None:
                del generated_audio

            gc.collect()

            torch.cuda.empty_cache()

            write_report(report)

    report["completed_at"] = (
        datetime.now().isoformat()
    )

    report["passed_count"] = passed_count
    report["total_count"] = len(
        BENCHMARKS
    )

    write_report(report)

    print("\n" + "=" * 80)
    print("GPU BENCHMARK COMPLETE")
    print("=" * 80)

    print(
        "Passed:",
        passed_count,
        "of",
        len(BENCHMARKS),
    )

    print("Report:", REPORT_PATH)

    return (
        0
        if passed_count == len(BENCHMARKS)
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
