from __future__ import annotations

import hashlib
import math
import tempfile
import wave
from array import array
from pathlib import Path

from app.audio.joiner import WavJoinInput
from app.audio.joiner import WavJoiner


checks_passed = 0


def check(
    name: str,
    condition: bool,
    detail: str = "",
) -> None:
    global checks_passed

    if not condition:
        raise AssertionError(
            f"{name}: FAILED"
            + (
                f"\n{detail}"
                if detail
                else ""
            )
        )

    checks_passed += 1
    print(f"{name}: PASSED")


def check_raises(
    name: str,
    expected_error: type[BaseException],
    function,
    message_marker: str,
) -> None:
    global checks_passed

    try:
        function()

    except expected_error as error:
        if message_marker.lower() not in str(error).lower():
            raise AssertionError(
                f"{name}: wrong error message\n"
                f"Expected marker: {message_marker!r}\n"
                f"Actual: {str(error)!r}"
            ) from error

        checks_passed += 1
        print(f"{name}: PASSED")
        return

    except Exception as error:
        raise AssertionError(
            f"{name}: expected "
            f"{expected_error.__name__}, "
            f"received {type(error).__name__}: {error}"
        ) from error

    raise AssertionError(
        f"{name}: expected "
        f"{expected_error.__name__}, "
        "but no exception was raised."
    )


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for block in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def write_constant_wav(
    path: Path,
    *,
    amplitude: int,
    duration_ms: int = 100,
    sample_rate: int = 24_000,
    channels: int = 1,
    sample_width: int = 2,
) -> None:
    frame_count = round(
        sample_rate
        * duration_ms
        / 1000
    )

    with wave.open(
        str(path),
        "wb",
    ) as wav_file:
        wav_file.setnchannels(
            channels
        )

        wav_file.setsampwidth(
            sample_width
        )

        wav_file.setframerate(
            sample_rate
        )

        if sample_width == 2:
            samples = array(
                "h",
            )

            for _ in range(
                frame_count
            ):
                for _channel in range(
                    channels
                ):
                    samples.append(
                        amplitude
                    )

            wav_file.writeframes(
                samples.tobytes()
            )

        else:
            wav_file.writeframes(
                bytes(
                    [128]
                    * frame_count
                    * channels
                )
            )


def read_wav(
    path: Path,
) -> tuple[
    dict[str, int],
    array,
]:
    with wave.open(
        str(path),
        "rb",
    ) as wav_file:
        metadata = {
            "channels": wav_file.getnchannels(),
            "sample_width": wav_file.getsampwidth(),
            "sample_rate": wav_file.getframerate(),
            "frames": wav_file.getnframes(),
        }

        samples = array(
            "h",
        )

        samples.frombytes(
            wav_file.readframes(
                wav_file.getnframes()
            )
        )

    return metadata, samples


print("=" * 84)
print("MILESTONE 10.6 WAV JOINER CONTRACT")
print("=" * 84)

with tempfile.TemporaryDirectory(
    prefix="milestone10_6_joiner_"
) as temporary_directory:
    root = Path(
        temporary_directory
    )

    single_source = (
        root / "single.wav"
    )

    single_output = (
        root / "single_joined.wav"
    )

    write_constant_wav(
        single_source,
        amplitude=6000,
    )

    single_source_hash = sha256_file(
        single_source
    )

    single_result = WavJoiner.join(
        [
            WavJoinInput(
                path=single_source,
                boundary_after="none",
            )
        ],
        single_output,
    )

    single_metadata, single_samples = (
        read_wav(
            single_output
        )
    )

    check(
        "Single joined WAV exists",
        single_output.exists(),
    )

    check(
        "Single WAV format",
        single_metadata
        == {
            "channels": 1,
            "sample_width": 2,
            "sample_rate": 24_000,
            "frames": 2400,
        },
        repr(single_metadata),
    )

    check(
        "Single WAV metadata segment count",
        single_result["segment_count"]
        == 1,
    )

    check(
        "Fade-in begins at zero",
        single_samples[0] == 0,
        repr(single_samples[0]),
    )

    check(
        "Fade-out ends at zero",
        single_samples[-1] == 0,
        repr(single_samples[-1]),
    )

    check(
        "Single source remains unchanged",
        sha256_file(single_source)
        == single_source_hash,
    )

    first = root / "first.wav"
    second = root / "second.wav"
    third = root / "third.wav"
    joined = root / "joined.wav"

    write_constant_wav(
        first,
        amplitude=4000,
    )

    write_constant_wav(
        second,
        amplitude=-7000,
    )

    write_constant_wav(
        third,
        amplitude=10000,
    )

    first_hash = sha256_file(
        first
    )

    second_hash = sha256_file(
        second
    )

    third_hash = sha256_file(
        third
    )

    multi_inputs = [
        WavJoinInput(
            path=first,
            boundary_after="continuation",
        ),
        WavJoinInput(
            path=second,
            boundary_after="sentence",
        ),
        WavJoinInput(
            path=third,
            boundary_after="none",
        ),
    ]

    multi_result = WavJoiner.join(
        multi_inputs,
        joined,
    )

    multi_metadata, multi_samples = (
        read_wav(
            joined
        )
    )

    expected_frames = (
        2400
        + 1440
        + 2400
        + 4320
        + 2400
    )

    check(
        "Multiple segment count",
        multi_result["segment_count"]
        == 3,
    )

    check(
        "Pause plan is preserved",
        multi_result[
            "pause_milliseconds"
        ]
        == [
            60,
            180,
            0,
        ],
        repr(
            multi_result[
                "pause_milliseconds"
            ]
        ),
    )

    check(
        "Multiple WAV output format",
        (
            multi_metadata["channels"] == 1
            and multi_metadata["sample_width"] == 2
            and multi_metadata["sample_rate"] == 24_000
        ),
        repr(multi_metadata),
    )

    check(
        "Multiple WAV exact frame count",
        multi_metadata["frames"]
        == expected_frames,
        (
            f"Expected={expected_frames}; "
            f"Actual={multi_metadata['frames']}"
        ),
    )

    first_middle = 1200

    second_start = (
        2400 + 1440
    )

    second_middle = (
        second_start + 1200
    )

    third_start = (
        second_start
        + 2400
        + 4320
    )

    third_middle = (
        third_start + 1200
    )

    check(
        "First segment order preserved",
        multi_samples[first_middle]
        == 4000,
        repr(
            multi_samples[first_middle]
        ),
    )

    check(
        "Second segment order preserved",
        multi_samples[second_middle]
        == -7000,
        repr(
            multi_samples[second_middle]
        ),
    )

    check(
        "Third segment order preserved",
        multi_samples[third_middle]
        == 10000,
        repr(
            multi_samples[third_middle]
        ),
    )

    check(
        "No trailing pause is added",
        multi_result[
            "pause_milliseconds"
        ][-1]
        == 0,
    )

    paragraph_output = (
        root / "paragraph.wav"
    )

    paragraph_result = WavJoiner.join(
        [
            WavJoinInput(
                path=first,
                boundary_after="paragraph",
            ),
            WavJoinInput(
                path=second,
                boundary_after="none",
            ),
        ],
        paragraph_output,
    )

    paragraph_metadata, _ = read_wav(
        paragraph_output
    )

    expected_paragraph_frames = (
        2400
        + 8400
        + 2400
    )

    check(
        "Paragraph pause uses 350 ms",
        paragraph_result[
            "pause_milliseconds"
        ]
        == [
            350,
            0,
        ],
    )

    check(
        "Paragraph frame count is exact",
        paragraph_metadata["frames"]
        == expected_paragraph_frames,
        (
            f"Expected={expected_paragraph_frames}; "
            f"Actual={paragraph_metadata['frames']}"
        ),
    )

    check(
        "First source still unchanged",
        sha256_file(first)
        == first_hash,
    )

    check(
        "Second source still unchanged",
        sha256_file(second)
        == second_hash,
    )

    check(
        "Third source still unchanged",
        sha256_file(third)
        == third_hash,
    )

    deterministic_output = (
        root / "deterministic.wav"
    )

    WavJoiner.join(
        multi_inputs,
        deterministic_output,
    )

    check(
        "Joining is deterministic",
        sha256_file(
            deterministic_output
        )
        == sha256_file(
            joined
        ),
    )

    check_raises(
        "Empty input list is rejected",
        ValueError,
        lambda: WavJoiner.join(
            [],
            root / "empty.wav",
        ),
        "At least one",
    )

    check_raises(
        "Missing input is rejected",
        FileNotFoundError,
        lambda: WavJoiner.join(
            [
                WavJoinInput(
                    path=root / "missing.wav",
                    boundary_after="none",
                )
            ],
            root / "missing_output.wav",
        ),
        "not found",
    )

    stereo_source = (
        root / "stereo.wav"
    )

    write_constant_wav(
        stereo_source,
        amplitude=1000,
        channels=2,
    )

    check_raises(
        "Stereo input is rejected",
        ValueError,
        lambda: WavJoiner.join(
            [
                WavJoinInput(
                    path=stereo_source,
                    boundary_after="none",
                )
            ],
            root / "stereo_output.wav",
        ),
        "mono",
    )

    wrong_rate_source = (
        root / "wrong_rate.wav"
    )

    write_constant_wav(
        wrong_rate_source,
        amplitude=1000,
        sample_rate=16_000,
    )

    check_raises(
        "Wrong sample rate is rejected",
        ValueError,
        lambda: WavJoiner.join(
            [
                WavJoinInput(
                    path=wrong_rate_source,
                    boundary_after="none",
                )
            ],
            root / "wrong_rate_output.wav",
        ),
        "24000",
    )

    wrong_width_source = (
        root / "wrong_width.wav"
    )

    write_constant_wav(
        wrong_width_source,
        amplitude=0,
        sample_width=1,
    )

    check_raises(
        "Non-PCM16 input is rejected",
        ValueError,
        lambda: WavJoiner.join(
            [
                WavJoinInput(
                    path=wrong_width_source,
                    boundary_after="none",
                )
            ],
            root / "wrong_width_output.wav",
        ),
        "PCM16",
    )

    check_raises(
        "Final non-none boundary is rejected",
        ValueError,
        lambda: WavJoiner.join(
            [
                WavJoinInput(
                    path=first,
                    boundary_after="sentence",
                )
            ],
            root / "invalid_final.wav",
        ),
        "final WAV segment",
    )

    check_raises(
        "Output cannot replace a source",
        ValueError,
        lambda: WavJoiner.join(
            [
                WavJoinInput(
                    path=first,
                    boundary_after="none",
                )
            ],
            first,
        ),
        "cannot be one",
    )

    invalid_boundary_input = WavJoinInput(
        path=first,
        boundary_after="invalid",  # type: ignore[arg-type]
    )

    check_raises(
        "Invalid boundary is rejected",
        ValueError,
        lambda: WavJoiner.join(
            [
                invalid_boundary_input
            ],
            root / "invalid_boundary.wav",
        ),
        "unsupported",
    )

    temporary_files = list(
        root.glob(
            "*.join_tmp.wav"
        )
    )

    check(
        "Temporary join files are cleaned",
        temporary_files == [],
        repr(temporary_files),
    )

print()
print("=" * 84)
print(
    "MILESTONE 10.6 WAV JOINER CONTRACT: PASSED"
)
print("=" * 84)
print("Checks passed:", checks_passed)
