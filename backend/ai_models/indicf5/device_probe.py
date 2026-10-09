from __future__ import annotations

import gc
import sys
import time
from collections import Counter
from typing import Any

import torch
from transformers import AutoModel


MODEL_ID = "ai4bharat/IndicF5"

COMMON_MODULE_ATTRIBUTES = (
    "model",
    "ema_model",
    "transformer",
    "vocoder",
    "generator",
    "mel_spec",
    "decoder",
    "encoder",
    "tts_model",
)


def count_module_devices(
    module: torch.nn.Module,
) -> tuple[Counter[str], Counter[str], int]:
    tensor_counts: Counter[str] = Counter()
    parameter_counts: Counter[str] = Counter()

    total_parameters = 0

    for parameter in module.parameters(
        recurse=True
    ):
        device = str(parameter.device)
        parameter_count = parameter.numel()

        tensor_counts[device] += 1
        parameter_counts[device] += parameter_count
        total_parameters += parameter_count

    return (
        tensor_counts,
        parameter_counts,
        total_parameters,
    )


def inspect_candidate(
    label: str,
    candidate: Any,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "label": label,
        "type": type(candidate).__name__,
        "is_torch_module": isinstance(
            candidate,
            torch.nn.Module,
        ),
    }

    if not isinstance(
        candidate,
        torch.nn.Module,
    ):
        return result

    (
        tensor_counts,
        parameter_counts,
        total_parameters,
    ) = count_module_devices(candidate)

    result["tensor_devices"] = dict(
        tensor_counts
    )

    result["parameter_devices"] = dict(
        parameter_counts
    )

    result["total_parameters"] = (
        total_parameters
    )

    return result


def main() -> int:
    print("=" * 80)
    print("INDICF5 DEVICE PROBE")
    print("=" * 80)

    print("Python:", sys.version.split()[0])
    print("Torch:", torch.__version__)
    print("CUDA available:", torch.cuda.is_available())

    if torch.cuda.is_available():
        print(
            "GPU:",
            torch.cuda.get_device_name(0),
        )

        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()

    gc.collect()

    print("\nLoading model...")

    started = time.perf_counter()

    model = AutoModel.from_pretrained(
        MODEL_ID,
        trust_remote_code=True,
    )

    load_seconds = (
        time.perf_counter() - started
    )

    print(
        "Model load time:",
        round(load_seconds, 2),
        "seconds",
    )

    candidates: list[
        tuple[str, Any]
    ] = [
        ("wrapper", model),
    ]

    seen_ids = {
        id(model),
    }

    for attribute_name in (
        COMMON_MODULE_ATTRIBUTES
    ):
        candidate = getattr(
            model,
            attribute_name,
            None,
        )

        if candidate is None:
            continue

        if id(candidate) in seen_ids:
            continue

        seen_ids.add(
            id(candidate)
        )

        candidates.append(
            (
                f"wrapper.{attribute_name}",
                candidate,
            )
        )

        for nested_name in (
            COMMON_MODULE_ATTRIBUTES
        ):
            nested_candidate = getattr(
                candidate,
                nested_name,
                None,
            )

            if nested_candidate is None:
                continue

            if id(nested_candidate) in seen_ids:
                continue

            seen_ids.add(
                id(nested_candidate)
            )

            candidates.append(
                (
                    (
                        f"wrapper.{attribute_name}"
                        f".{nested_name}"
                    ),
                    nested_candidate,
                )
            )

    overall_parameters: Counter[str] = (
        Counter()
    )

    exposed_module_count = 0

    print("\nDiscovered objects:")

    for label, candidate in candidates:
        result = inspect_candidate(
            label,
            candidate,
        )

        print("\n" + "-" * 80)
        print("Object:", result["label"])
        print("Type:", result["type"])
        print(
            "Torch module:",
            result["is_torch_module"],
        )

        if not result["is_torch_module"]:
            continue

        exposed_module_count += 1

        print(
            "Total parameters:",
            f"{result['total_parameters']:,}",
        )

        parameter_devices = result.get(
            "parameter_devices",
            {},
        )

        if not parameter_devices:
            print(
                "Parameter devices: none exposed"
            )

        for device, count in (
            parameter_devices.items()
        ):
            print(
                f"Parameters on {device}: "
                f"{count:,}"
            )

            overall_parameters[
                device
            ] += count

    print("\n" + "=" * 80)
    print("CUDA MEMORY AFTER MODEL LOAD")
    print("=" * 80)

    if torch.cuda.is_available():
        allocated = (
            torch.cuda.memory_allocated()
            / (1024 ** 2)
        )

        reserved = (
            torch.cuda.memory_reserved()
            / (1024 ** 2)
        )

        peak = (
            torch.cuda.max_memory_allocated()
            / (1024 ** 2)
        )

        print(
            "Allocated MB:",
            round(allocated, 2),
        )

        print(
            "Reserved MB:",
            round(reserved, 2),
        )

        print(
            "Peak allocated MB:",
            round(peak, 2),
        )

    print("\n" + "=" * 80)
    print("DEVICE PROBE RESULT")
    print("=" * 80)

    cpu_parameters = overall_parameters.get(
        "cpu",
        0,
    )

    cuda_parameters = sum(
        count
        for device, count
        in overall_parameters.items()
        if device.startswith("cuda")
    )

    print(
        "Exposed Torch modules:",
        exposed_module_count,
    )

    print(
        "CPU parameters:",
        f"{cpu_parameters:,}",
    )

    print(
        "CUDA parameters:",
        f"{cuda_parameters:,}",
    )

    if cuda_parameters > 0:
        print(
            "RESULT: GPU PARAMETERS DETECTED"
        )

        print(
            "The model is at least partially "
            "loaded on CUDA."
        )

    elif cpu_parameters > 0:
        print(
            "RESULT: CPU-ONLY PARAMETERS DETECTED"
        )

        print(
            "The current IndicF5 loading path "
            "places exposed parameters on CPU."
        )

    else:
        print(
            "RESULT: WRAPPER HIDES MODEL PARAMETERS"
        )

        print(
            "Runtime GPU monitoring is required "
            "during inference."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
