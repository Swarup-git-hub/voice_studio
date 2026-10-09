from __future__ import annotations

import gc
import json
import sys
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

TEST_TEXT = (
    "ఇది ఇండిక్ ఎఫ్ ఫైవ్ "
    "జీ పీ యూ పనితీరు పరీక్ష."
)

OUTPUT_AUDIO = (
    OUTPUT_FOLDER
    / "indicf5_gpu_probe_telugu.wav"
)

REPORT_PATH = (
    OUTPUT_FOLDER
    / "gpu_move_probe_results.json"
)


def synchronize_cuda() -> None:
    if torch.cuda.is_available():
        torch.cuda.synchronize()


def bytes_to_mb(value: int) -> float:
    return round(
        value / (1024 ** 2),
        2,
    )


def collect_devices(
    module: torch.nn.Module,
) -> dict[str, Any]:
    parameter_counts: Counter[str] = Counter()
    parameter_tensors: Counter[str] = Counter()

    total_parameters = 0
    meta_parameters = 0

    for parameter in module.parameters():
        device_name = str(
            parameter.device
        )

        count = parameter.numel()

        parameter_counts[
            device_name
        ] += count

        parameter_tensors[
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
        "parameter_tensors": dict(
            parameter_tensors
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
            "Unexpected generated-audio shape: "
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


def save_report(
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
        "test_text": TEST_TEXT,
        "load": {},
        "move": {},
        "inference": {},
    }

    print("=" * 80)
    print("INDICF5 SAFE GPU MOVEMENT PROBE")
    print("=" * 80)

    print("Python:", sys.version.split()[0])
    print("Torch:", torch.__version__)
    print(
        "CUDA available:",
        torch.cuda.is_available(),
    )

    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is not available."
        )

    print(
        "GPU:",
        torch.cuda.get_device_name(0),
    )

    if not REFERENCE_AUDIO.exists():
        raise FileNotFoundError(
            "Reference audio was not found:\n"
            f"{REFERENCE_AUDIO}"
        )

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    gc.collect()

    print(
        "\nLoading IndicF5 using its "
        "default loading behavior..."
    )

    load_started = time.perf_counter()

    try:
        model = AutoModel.from_pretrained(
            MODEL_ID,
            trust_remote_code=True,
        )

    except Exception as error:
        report["load"] = {
            "status": "failed",
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }

        save_report(report)

        print("\nMODEL LOAD FAILED")
        print(type(error).__name__)
        print(str(error))

        return 1

    load_seconds = round(
        time.perf_counter()
        - load_started,
        2,
    )

    before_move = collect_devices(
        model
    )

    report["load"] = {
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
        "Parameters before GPU move:",
        before_move["parameter_counts"],
    )

    print(
        "Meta parameters before move:",
        before_move["meta_parameters"],
    )

    print(
        "\nAttempting model.to(cuda:0)..."
    )

    move_started = time.perf_counter()

    try:
        model = model.to(
            TARGET_DEVICE
        )

        model.eval()

        synchronize_cuda()

    except Exception as error:
        report["move"] = {
            "status": "failed",
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }

        save_report(report)

        print("\nGPU MOVE FAILED")
        print(
            "Error type:",
            type(error).__name__,
        )
        print(
            "Error:",
            str(error),
        )
        print(
            "Report:",
            REPORT_PATH,
        )

        return 2

    move_seconds = round(
        time.perf_counter()
        - move_started,
        2,
    )

    after_move = collect_devices(
        model
    )

    allocated_after_move = bytes_to_mb(
        torch.cuda.memory_allocated()
    )

    reserved_after_move = bytes_to_mb(
        torch.cuda.memory_reserved()
    )

    report["move"] = {
        "status": "passed",
        "seconds": move_seconds,
        "devices": after_move,
        "allocated_mb": allocated_after_move,
        "reserved_mb": reserved_after_move,
    }

    print(
        "GPU move time:",
        move_seconds,
        "seconds",
    )

    print(
        "Parameters after GPU move:",
        after_move["parameter_counts"],
    )

    print(
        "Meta parameters after move:",
        after_move["meta_parameters"],
    )

    print(
        "CUDA allocated after move:",
        allocated_after_move,
        "MB",
    )

    print(
        "CUDA reserved after move:",
        reserved_after_move,
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

    cpu_parameters = (
        after_move[
            "parameter_counts"
        ].get(
            "cpu",
            0,
        )
    )

    print(
        "CUDA parameters:",
        f"{cuda_parameters:,}",
    )

    print(
        "CPU parameters:",
        f"{cpu_parameters:,}",
    )

    if cuda_parameters <= 0:
        report["move"][
            "status"
        ] = "failed"

        report["move"]["error"] = (
            "No CUDA parameters were detected "
            "after model.to(cuda:0)."
        )

        save_report(report)

        print(
            "\nRESULT: NO CUDA PARAMETERS "
            "DETECTED"
        )

        return 3

    if after_move[
        "meta_parameters"
    ] > 0:
        report["move"][
            "status"
        ] = "failed"

        report["move"]["error"] = (
            "Meta parameters remain after "
            "the GPU movement attempt."
        )

        save_report(report)

        print(
            "\nRESULT: META PARAMETERS REMAIN"
        )

        return 4

    print(
        "\nRunning one short Telugu "
        "GPU inference..."
    )

    torch.cuda.reset_peak_memory_stats()

    synchronize_cuda()

    inference_started = (
        time.perf_counter()
    )

    try:
        with torch.inference_mode():
            generated_audio = model(
                TEST_TEXT,
                ref_audio_path=str(
                    REFERENCE_AUDIO
                ),
                ref_text=(
                    REFERENCE_TRANSCRIPT
                ),
            )

        synchronize_cuda()

    except Exception as error:
        report["inference"] = {
            "status": "failed",
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
        }

        save_report(report)

        print("\nGPU INFERENCE FAILED")
        print(
            "Error type:",
            type(error).__name__,
        )
        print(
            "Error:",
            str(error),
        )
        print(
            "Report:",
            REPORT_PATH,
        )

        return 5

    inference_seconds = round(
        time.perf_counter()
        - inference_started,
        2,
    )

    audio = normalize_audio(
        generated_audio
    )

    sf.write(
        str(OUTPUT_AUDIO),
        audio,
        samplerate=24000,
        subtype="PCM_16",
    )

    if not OUTPUT_AUDIO.exists():
        raise RuntimeError(
            "GPU probe WAV was not created."
        )

    if OUTPUT_AUDIO.stat().st_size <= 0:
        raise RuntimeError(
            "GPU probe WAV is empty."
        )

    info = sf.info(
        str(OUTPUT_AUDIO)
    )

    peak_cuda_mb = bytes_to_mb(
        torch.cuda.max_memory_allocated()
    )

    current_cuda_mb = bytes_to_mb(
        torch.cuda.memory_allocated()
    )

    real_time_factor = round(
        inference_seconds
        / info.duration,
        2,
    )

    report["inference"] = {
        "status": "passed",
        "seconds": inference_seconds,
        "audio_duration_seconds": round(
            info.duration,
            3,
        ),
        "real_time_factor": (
            real_time_factor
        ),
        "sample_rate": info.samplerate,
        "channels": info.channels,
        "subtype": info.subtype,
        "output_file": str(
            OUTPUT_AUDIO
        ),
        "peak_cuda_mb": peak_cuda_mb,
        "current_cuda_mb": current_cuda_mb,
    }

    report["completed_at"] = (
        datetime.now().isoformat()
    )

    save_report(report)

    print("\n" + "=" * 80)
    print("GPU PROBE RESULT")
    print("=" * 80)

    print("GPU move status: PASSED")
    print("GPU inference status: PASSED")

    print(
        "Generation time:",
        inference_seconds,
        "seconds",
    )

    print(
        "Audio duration:",
        round(
            info.duration,
            3,
        ),
        "seconds",
    )

    print(
        "Real-time factor:",
        real_time_factor,
    )

    print(
        "Peak CUDA allocated:",
        peak_cuda_mb,
        "MB",
    )

    print(
        "Current CUDA allocated:",
        current_cuda_mb,
        "MB",
    )

    print(
        "Output:",
        OUTPUT_AUDIO,
    )

    print(
        "Report:",
        REPORT_PATH,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
