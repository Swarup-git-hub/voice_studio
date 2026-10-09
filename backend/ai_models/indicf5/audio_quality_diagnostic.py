from __future__ import annotations

import csv
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
OUTPUT_DIRECTORY = SCRIPT_DIRECTORY / "outputs"

JSON_REPORT_PATH = (
    OUTPUT_DIRECTORY
    / "audio_quality_diagnostic.json"
)

CSV_REPORT_PATH = (
    OUTPUT_DIRECTORY
    / "audio_quality_diagnostic.csv"
)

TARGET_FILES = {
    "english": "indicf5_gpu_english.wav",
    "telugu": "indicf5_gpu_telugu.wav",
    "mixed": "indicf5_gpu_mixed.wav",
}

CLIPPING_THRESHOLD = 0.999
NEAR_CLIPPING_THRESHOLD = 0.98
SILENCE_THRESHOLD = 0.0001
SIGNIFICANT_DC_OFFSET = 0.01


def amplitude_to_dbfs(
    amplitude: float,
) -> float:
    if amplitude <= 0:
        return -120.0

    return round(
        20.0 * math.log10(amplitude),
        2,
    )


def analyze_audio(
    language: str,
    path: Path,
) -> dict[str, Any]:
    audio, sample_rate = sf.read(
        str(path),
        dtype="float32",
        always_2d=True,
    )

    original_channels = int(
        audio.shape[1]
    )

    mono_audio = np.mean(
        audio,
        axis=1,
        dtype=np.float64,
    )

    finite = bool(
        np.isfinite(mono_audio).all()
    )

    safe_audio = np.nan_to_num(
        mono_audio,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    sample_count = int(
        safe_audio.size
    )

    if sample_count <= 0:
        raise ValueError(
            f"Audio file is empty: {path}"
        )

    absolute_audio = np.abs(
        safe_audio
    )

    peak = float(
        np.max(absolute_audio)
    )

    rms = float(
        np.sqrt(
            np.mean(
                np.square(safe_audio)
            )
        )
    )

    dc_offset = float(
        np.mean(safe_audio)
    )

    clipping_samples = int(
        np.count_nonzero(
            absolute_audio
            >= CLIPPING_THRESHOLD
        )
    )

    near_clipping_samples = int(
        np.count_nonzero(
            absolute_audio
            >= NEAR_CLIPPING_THRESHOLD
        )
    )

    silent_samples = int(
        np.count_nonzero(
            absolute_audio
            <= SILENCE_THRESHOLD
        )
    )

    clipping_percentage = (
        clipping_samples
        / sample_count
        * 100.0
    )

    near_clipping_percentage = (
        near_clipping_samples
        / sample_count
        * 100.0
    )

    silence_percentage = (
        silent_samples
        / sample_count
        * 100.0
    )

    duration_seconds = (
        sample_count
        / sample_rate
    )

    peak_dbfs = amplitude_to_dbfs(
        peak
    )

    rms_dbfs = amplitude_to_dbfs(
        rms
    )

    crest_factor_db = round(
        peak_dbfs - rms_dbfs,
        2,
    )

    issues: list[str] = []

    if not finite:
        issues.append(
            "invalid_non_finite_samples"
        )

    if clipping_samples > 0:
        issues.append(
            "digital_clipping_detected"
        )

    elif (
        near_clipping_percentage
        > 0.1
    ):
        issues.append(
            "frequent_near_clipping"
        )

    if abs(dc_offset) >= (
        SIGNIFICANT_DC_OFFSET
    ):
        issues.append(
            "significant_dc_offset"
        )

    if not issues:
        issues.append(
            "no_basic_waveform_fault_detected"
        )

    return {
        "language": language,
        "status": "analyzed",
        "file": path.name,
        "path": str(path),
        "file_size_bytes": (
            path.stat().st_size
        ),
        "sample_rate": int(
            sample_rate
        ),
        "original_channels": (
            original_channels
        ),
        "analyzed_channels": 1,
        "samples": sample_count,
        "duration_seconds": round(
            duration_seconds,
            3,
        ),
        "finite": finite,
        "minimum": round(
            float(np.min(safe_audio)),
            6,
        ),
        "maximum": round(
            float(np.max(safe_audio)),
            6,
        ),
        "peak": round(
            peak,
            6,
        ),
        "peak_dbfs": peak_dbfs,
        "rms": round(
            rms,
            6,
        ),
        "rms_dbfs": rms_dbfs,
        "crest_factor_db": (
            crest_factor_db
        ),
        "dc_offset": round(
            dc_offset,
            8,
        ),
        "clipping_samples": (
            clipping_samples
        ),
        "clipping_percentage": round(
            clipping_percentage,
            6,
        ),
        "near_clipping_samples": (
            near_clipping_samples
        ),
        "near_clipping_percentage": round(
            near_clipping_percentage,
            6,
        ),
        "silence_percentage": round(
            silence_percentage,
            3,
        ),
        "issues": issues,
    }


def save_json_report(
    report: dict[str, Any],
) -> None:
    JSON_REPORT_PATH.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def save_csv_report(
    results: list[dict[str, Any]],
) -> None:
    fieldnames = [
        "language",
        "status",
        "file",
        "sample_rate",
        "original_channels",
        "duration_seconds",
        "finite",
        "peak",
        "peak_dbfs",
        "rms",
        "rms_dbfs",
        "crest_factor_db",
        "dc_offset",
        "clipping_samples",
        "clipping_percentage",
        "near_clipping_samples",
        "near_clipping_percentage",
        "silence_percentage",
        "issues",
    ]

    with CSV_REPORT_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for result in results:
            row = {
                field: result.get(
                    field,
                    "",
                )
                for field in fieldnames
            }

            if isinstance(
                row.get("issues"),
                list,
            ):
                row["issues"] = ";".join(
                    row["issues"]
                )

            writer.writerow(row)


def main() -> int:
    print("=" * 80)
    print("INDICF5 GPU AUDIO QUALITY DIAGNOSTIC")
    print("=" * 80)

    print(
        "Output directory:",
        OUTPUT_DIRECTORY,
    )

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    results: list[
        dict[str, Any]
    ] = []

    missing_count = 0
    invalid_count = 0

    for language, filename in (
        TARGET_FILES.items()
    ):
        path = (
            OUTPUT_DIRECTORY
            / filename
        )

        print("\n" + "-" * 80)
        print("Language:", language)
        print("File    :", path)

        if not path.exists():
            missing_count += 1

            missing_result = {
                "language": language,
                "status": "missing",
                "file": filename,
                "path": str(path),
                "issues": [
                    "file_not_found"
                ],
            }

            results.append(
                missing_result
            )

            print("Status  : MISSING")
            continue

        try:
            result = analyze_audio(
                language,
                path,
            )

            results.append(
                result
            )

            if not result["finite"]:
                invalid_count += 1

            print(
                "Status                   : ANALYZED"
            )
            print(
                "Duration                 :",
                result["duration_seconds"],
                "seconds",
            )
            print(
                "Sample rate              :",
                result["sample_rate"],
            )
            print(
                "Channels                 :",
                result["original_channels"],
            )
            print(
                "Finite                   :",
                result["finite"],
            )
            print(
                "Peak                     :",
                result["peak"],
            )
            print(
                "Peak dBFS                :",
                result["peak_dbfs"],
            )
            print(
                "RMS                      :",
                result["rms"],
            )
            print(
                "RMS dBFS                 :",
                result["rms_dbfs"],
            )
            print(
                "Crest factor dB         :",
                result["crest_factor_db"],
            )
            print(
                "DC offset                :",
                result["dc_offset"],
            )
            print(
                "Clipping samples         :",
                result["clipping_samples"],
            )
            print(
                "Clipping percentage      :",
                result["clipping_percentage"],
            )
            print(
                "Near-clipping percentage :",
                result[
                    "near_clipping_percentage"
                ],
            )
            print(
                "Silence percentage       :",
                result["silence_percentage"],
            )
            print(
                "Diagnostic issues        :",
                ", ".join(
                    result["issues"]
                ),
            )

        except Exception as error:
            invalid_count += 1

            error_result = {
                "language": language,
                "status": "failed",
                "file": filename,
                "path": str(path),
                "error_type": type(
                    error
                ).__name__,
                "error": str(error),
                "issues": [
                    "diagnostic_failed"
                ],
            }

            results.append(
                error_result
            )

            print("Status  : FAILED")
            print(
                "Error   :",
                type(error).__name__,
                str(error),
            )

    report = {
        "created_at": (
            datetime.now().isoformat()
        ),
        "output_directory": str(
            OUTPUT_DIRECTORY
        ),
        "files_expected": len(
            TARGET_FILES
        ),
        "files_missing": (
            missing_count
        ),
        "files_invalid": (
            invalid_count
        ),
        "results": results,
    }

    save_json_report(
        report
    )

    save_csv_report(
        results
    )

    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)

    print(
        "Expected files:",
        len(TARGET_FILES),
    )
    print(
        "Missing files :",
        missing_count,
    )
    print(
        "Invalid files :",
        invalid_count,
    )
    print(
        "JSON report   :",
        JSON_REPORT_PATH,
    )
    print(
        "CSV report    :",
        CSV_REPORT_PATH,
    )

    if missing_count > 0:
        return 2

    if invalid_count > 0:
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
