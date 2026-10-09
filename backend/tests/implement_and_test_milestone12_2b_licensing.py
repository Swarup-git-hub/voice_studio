from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(
    os.environ[
        "MILESTONE12_2B_PROJECT_ROOT"
    ]
).resolve()

BACKEND_ROOT = (
    PROJECT_ROOT
    / "backend"
)

SOURCE_LICENSE_PATH = (
    BACKEND_ROOT
    / "ai_models"
    / "cosyvoice"
    / "LICENSE"
)

LICENSE_PATH = (
    PROJECT_ROOT
    / "LICENSE"
)

NOTICE_PATH = (
    PROJECT_ROOT
    / "NOTICE"
)

LICENSING_PATH = (
    PROJECT_ROOT
    / "LICENSING.md"
)

THIRD_PARTY_PATH = (
    PROJECT_ROOT
    / "THIRD_PARTY_NOTICES.md"
)

MODEL_TERMS_PATH = (
    PROJECT_ROOT
    / "MODEL_AND_DATA_TERMS.md"
)

REPORT_PATH = Path(
    os.environ[
        "MILESTONE12_2B_REPORT_PATH"
    ]
).resolve()


checks_passed = 0


def check(
    name: str,
    condition: bool,
    detail: str = "",
) -> None:
    global checks_passed

    if not condition:
        message = f"{name}: FAILED"

        if detail:
            message += f"\n{detail}"

        raise AssertionError(
            message
        )

    checks_passed += 1

    print(
        f"{name}: PASSED"
    )


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as source_file:
        while True:
            chunk = source_file.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(
                chunk
            )

    return digest.hexdigest()


def runtime_snapshot() -> dict[str, Any]:
    directories = {
        "voices": (
            BACKEND_ROOT
            / "app"
            / "voices"
        ),
        "outputs": (
            BACKEND_ROOT
            / "app"
            / "outputs"
        ),
        "logs": (
            PROJECT_ROOT
            / "logs"
        ),
    }

    snapshot: dict[str, Any] = {}

    for name, directory in directories.items():
        file_count = 0
        total_bytes = 0

        if directory.exists():
            for path in directory.rglob(
                "*"
            ):
                if not path.is_file():
                    continue

                file_count += 1
                total_bytes += path.stat().st_size

        snapshot[
            name
        ] = {
            "file_count": file_count,
            "total_bytes": total_bytes,
        }

    database_path = (
        BACKEND_ROOT
        / "voice.db"
    )

    snapshot[
        "database"
    ] = {
        "exists": database_path.exists(),
        "size_bytes": (
            database_path.stat().st_size
            if database_path.exists()
            else 0
        ),
    }

    return snapshot


def port_is_open(
    port: int,
) -> bool:
    try:
        with socket.create_connection(
            (
                "127.0.0.1",
                port,
            ),
            timeout=0.5,
        ):
            return True

    except OSError:
        return False


def contains_windows_absolute_path(
    text: str,
) -> bool:
    return (
        re.search(
            r"(?m)^[A-Za-z]:[\\/]",
            text,
        )
        is not None
    )


print("=" * 92)
print(
    "MILESTONE 12.2B — LICENCE DECISION "
    "AND THIRD-PARTY NOTICES"
)
print("=" * 92)


before_snapshot = runtime_snapshot()


check(
    "CosyVoice source licence exists",
    SOURCE_LICENSE_PATH.exists(),
    str(
        SOURCE_LICENSE_PATH
    ),
)


source_license = (
    SOURCE_LICENSE_PATH.read_text(
        encoding="utf-8-sig",
        errors="replace",
    )
)


check(
    "CosyVoice source licence is Apache 2.0",
    (
        "Apache License"
        in source_license
        and "Version 2.0"
        in source_license
    ),
)


# The standard Apache 2.0 text already present in the
# CosyVoice repository is copied exactly to the project root.
shutil.copyfile(
    SOURCE_LICENSE_PATH,
    LICENSE_PATH,
)


NOTICE_PATH.write_text(
    """AI Voice Studio
Copyright 2026 Swarup Bande

Licensed under the Apache License, Version 2.0.

This distribution may use third-party software and separately
licensed machine-learning models. See THIRD_PARTY_NOTICES.md,
MODEL_AND_DATA_TERMS.md, and the licence files retained with
individual third-party components.
""",
    encoding="utf-8",
)


LICENSING_PATH.write_text(
    """# AI Voice Studio Licensing

## Project licence

Original AI Voice Studio application code and documentation
authored specifically for this repository are licensed under the
Apache License, Version 2.0, except where another licence or
copyright notice is explicitly stated.

The full licence text is stored in the root `LICENSE` file. The
project copyright notice is stored in `NOTICE`.

## Why Apache-2.0 was selected

Apache-2.0 is a permissive open-source licence that supports
private use, modification, redistribution and commercial use. It
also contains explicit patent-licence terms.

This choice aligns with the primary CosyVoice source repository,
which is also Apache-2.0.

## What the project licence does not cover

The root Apache-2.0 licence does not replace, relicense or grant
rights over:

- Third-party source code and libraries.
- Python or JavaScript dependencies.
- CosyVoice or IndicF5 model weights.
- Model code downloaded from external model providers.
- Training or evaluation datasets.
- User-uploaded voice recordings.
- Speaker identity, personality or publicity rights.
- Generated narration owned or controlled by users.
- Trademarks, logos or project names owned by third parties.

Each of those items remains subject to its own licence, model card,
terms of access, consent requirements and applicable law.

## Distribution rules

A public source release must retain:

- `LICENSE`
- `NOTICE`
- `LICENSING.md`
- `THIRD_PARTY_NOTICES.md`
- `MODEL_AND_DATA_TERMS.md`
- Licence files included in vendored third-party source trees

A public release must not include:

- `.env` secrets
- Python virtual environments
- `node_modules`
- Personal reference voices
- Generated narration files
- The populated SQLite database
- Service logs
- Model caches or model weights
- Local FFmpeg executables
- Internal milestone backups and reports

Model weights must be downloaded independently from their official
provider so that every user accepts the current provider terms.

## Commercial deployment

The project licence permits commercial use of the original
AI Voice Studio code. Commercial deployment remains conditional
on compliance with every third-party software licence, model term,
dataset condition, voice-consent obligation and applicable law.

This document is project-maintenance guidance and is not a
substitute for professional legal advice.
""",
    encoding="utf-8",
)


THIRD_PARTY_PATH.write_text(
    """# Third-Party Notices

This file records focused third-party licence evidence relevant to
the current AI Voice Studio implementation.

It does not replace the complete licence text shipped with an
individual package, repository, model or binary.

## CosyVoice

- Component: FunAudioLLM CosyVoice source repository
- Use: Local voice-generation inference service
- Licence: Apache License 2.0
- Local licence: `backend/ai_models/cosyvoice/LICENSE`
- Official source: https://github.com/FunAudioLLM/CosyVoice

The repository also contains separately licensed third-party code:

- Matcha-TTS — MIT License
- HiFi-GAN components — MIT License

Their original licence files remain inside the CosyVoice
`third_party` directory and must not be removed.

## IndicF5

- Component: `ai4bharat/IndicF5`
- Use: Telugu and Indian-language voice generation
- Model-card licence: MIT
- Provider: AI4Bharat on Hugging Face
- Official model card: https://huggingface.co/ai4bharat/IndicF5

IndicF5 is gated. Users must obtain access from the official
provider and accept the provider's current conditions themselves.

The model card requires explicit permission for every voice being
cloned. The MIT identifier does not grant rights over a person's
voice or identity.

## FastAPI

- Use: Main backend and model-service HTTP APIs
- Licence: MIT
- Official source: https://github.com/fastapi/fastapi

## Pydantic

- Use: Request, response and configuration validation
- Licence: MIT
- Official source: https://github.com/pydantic/pydantic

Some installed Pydantic distributions did not expose a useful
licence field through local package metadata. The official source
repository supplies the authoritative MIT licence.

## NumPy

- Use: Numerical and audio-array processing
- Main licence: BSD 3-Clause
- Official licence: https://numpy.org/doc/stable/license

NumPy binary distributions may include separately licensed binary
components and their corresponding notices. The local audit found
a notice for `libquadmath` under LGPL-2.1-or-later.

Those bundled notices apply to the relevant component. They do not
automatically relicense the original AI Voice Studio source code.

Do not delete licence files distributed with NumPy wheels or binary
packages.

## FFmpeg

- Use: Audio conversion, validation, trimming and filtering
- Deployment type: External command-line prerequisite
- Official legal guidance: https://ffmpeg.org/legal.html

The current local Windows FFmpeg build reports `--enable-gpl`.
Therefore that particular FFmpeg executable must not be copied into
the AI Voice Studio source-release archive.

Users install FFmpeg separately and are responsible for complying
with the licence of their selected FFmpeg build.

AI Voice Studio invokes FFmpeg as an external executable and does
not include the executable in the repository release.

## Package-manager dependencies

Python and frontend dependencies are installed from their package
managers. Virtual environments and `node_modules` are excluded from
the source release.

A final release-validation step will preserve the generated
dependency inventory and verify that no dependency binaries are
accidentally bundled.
""",
    encoding="utf-8",
)


MODEL_TERMS_PATH.write_text(
    """# Model, Dataset and Voice Terms

## Purpose

AI Voice Studio integrates independently licensed speech models.
The root software licence applies only to original project code and
does not grant ownership of models, datasets, voices or identities.

## IndicF5

The configured model family is `ai4bharat/IndicF5`.

The official model card is marked MIT, but access is gated and is
subject to provider conditions. The model card requires users to
clone only voices for which they have explicit permission.

Model weights are not included in the public AI Voice Studio source
release.

## CosyVoice

The integrated CosyVoice source repository is Apache-2.0.

CosyVoice model artefacts must be obtained from an official
provider. The exact model card and provider terms applicable to the
downloaded model artefact must be reviewed at download and
deployment time.

CosyVoice model weights are not included in the public source
release.

## Training datasets

References to datasets in a model card do not grant AI Voice Studio
or its users ownership of those datasets.

Dataset licences, consent conditions and usage restrictions remain
independent from the software and model licences.

AI Voice Studio does not redistribute the IndicF5 or CosyVoice
training datasets.

## Voice recordings and speaker identity

A software or model licence does not grant permission to clone a
person's voice.

A user may upload or clone a voice only when the user:

1. Owns the recording and the relevant voice rights; or
2. Has explicit, informed permission from the speaker.

The user must not use AI Voice Studio for impersonation, fraud,
harassment, deceptive attribution or unauthorised voice cloning.

Reference recordings, transcripts and generated audio must be
treated as sensitive personal data.

## Generated audio

Generated audio is not automatically covered by the root project
licence. Rights and responsibilities depend on:

- The source text.
- The reference voice and speaker consent.
- The model-provider terms.
- Applicable copyright, privacy and personality-rights law.

Synthetic audio should be disclosed as AI-generated where the
context could otherwise mislead listeners.

## Deployment release gate

Before public deployment:

- Model access must use official provider accounts.
- Model weights must remain outside the source repository.
- Authentication and access control must be enabled.
- Users must accept the voice-use policy.
- Voice and generated-audio deletion must remain functional.
- Storage retention rules must be documented.
- Provider and model terms must be rechecked for changes.

This document is responsible-use and release guidance, not legal
advice.
""",
    encoding="utf-8",
)


after_snapshot = runtime_snapshot()


check(
    "Root Apache licence was created",
    LICENSE_PATH.exists(),
)

check(
    "Root licence exactly matches the local Apache licence text",
    (
        sha256_file(
            LICENSE_PATH
        )
        == sha256_file(
            SOURCE_LICENSE_PATH
        )
    ),
)

check(
    "Root licence identifies Apache License 2.0",
    (
        "Apache License"
        in LICENSE_PATH.read_text(
            encoding="utf-8-sig",
            errors="replace",
        )
        and "Version 2.0"
        in LICENSE_PATH.read_text(
            encoding="utf-8-sig",
            errors="replace",
        )
    ),
)

check(
    "NOTICE was created",
    NOTICE_PATH.exists(),
)

notice_source = NOTICE_PATH.read_text(
    encoding="utf-8"
)

check(
    "NOTICE records the project copyright",
    (
        "Copyright 2026 Swarup Bande"
        in notice_source
    ),
)

check(
    "LICENSING document was created",
    LICENSING_PATH.exists(),
)

licensing_source = (
    LICENSING_PATH.read_text(
        encoding="utf-8"
    )
)

check(
    "Licensing scope is limited to original project work",
    (
        "Original AI Voice Studio application code"
        in licensing_source
    ),
)

check(
    "Licensing exclusions cover models and user voices",
    (
        "model weights"
        in licensing_source.lower()
        and "voice recordings"
        in licensing_source.lower()
    ),
)

check(
    "Third-party notices were created",
    THIRD_PARTY_PATH.exists(),
)

third_party_source = (
    THIRD_PARTY_PATH.read_text(
        encoding="utf-8"
    )
)

for name, marker in {
    "CosyVoice Apache notice": (
        "FunAudioLLM CosyVoice"
    ),
    "Matcha-TTS MIT notice": (
        "Matcha-TTS"
    ),
    "HiFi-GAN MIT notice": (
        "HiFi-GAN"
    ),
    "IndicF5 MIT notice": (
        "ai4bharat/IndicF5"
    ),
    "FastAPI MIT notice": (
        "## FastAPI"
    ),
    "Pydantic MIT notice": (
        "## Pydantic"
    ),
    "NumPy BSD notice": (
        "BSD 3-Clause"
    ),
    "FFmpeg external-prerequisite notice": (
        "External command-line prerequisite"
    ),
}.items():
    check(
        name,
        marker in third_party_source,
        marker,
    )


check(
    "GPL-enabled FFmpeg is explicitly excluded from release",
    (
        "--enable-gpl"
        in third_party_source
        and "must not be copied"
        in third_party_source
    ),
)

check(
    "Model and data terms were created",
    MODEL_TERMS_PATH.exists(),
)

model_terms_source = (
    MODEL_TERMS_PATH.read_text(
        encoding="utf-8"
    )
)

check(
    "Explicit voice permission is required",
    (
        "explicit permission"
        in model_terms_source.lower()
    ),
)

check(
    "Model weights are excluded from source release",
    (
        model_terms_source.lower().count(
            "model weights are not included"
        )
        >= 2
    ),
)

check(
    "Dataset rights remain independent",
    (
        "dataset licences"
        in model_terms_source.lower()
    ),
)

check(
    "User voice data is outside the software licence",
    (
        "does not grant permission"
        in model_terms_source.lower()
    ),
)


release_documents = {
    "NOTICE": notice_source,
    "LICENSING.md": licensing_source,
    "THIRD_PARTY_NOTICES.md": (
        third_party_source
    ),
    "MODEL_AND_DATA_TERMS.md": (
        model_terms_source
    ),
}


unsafe_path_documents = {
    name: True
    for name, source in release_documents.items()
    if contains_windows_absolute_path(
        source
    )
}


check(
    "Release documents contain no personal Windows paths",
    not unsafe_path_documents,
    repr(
        unsafe_path_documents
    ),
)

check(
    "Private runtime data remained unchanged",
    before_snapshot == after_snapshot,
    (
        f"Before: {before_snapshot}\n"
        f"After: {after_snapshot}"
    ),
)


open_ports = [
    port
    for port in (
        5173,
        8000,
        8001,
        8002,
    )
    if port_is_open(
        port
    )
]


check(
    "No project services were started",
    not open_ports,
    repr(
        open_ports
    ),
)


report = {
    "milestone": "12.2B",
    "created_at": datetime.now().isoformat(),
    "licence_selected": "Apache-2.0",
    "copyright_holder": (
        "Swarup Bande"
    ),
    "copyright_year": 2026,
    "application_source_files_modified": False,
    "services_started": False,
    "release_documents_created": [
        str(
            LICENSE_PATH
        ),
        str(
            NOTICE_PATH
        ),
        str(
            LICENSING_PATH
        ),
        str(
            THIRD_PARTY_PATH
        ),
        str(
            MODEL_TERMS_PATH
        ),
    ],
    "model_weights_bundled": False,
    "ffmpeg_binary_bundled": False,
    "private_runtime_data_modified": False,
    "runtime_snapshot_before": before_snapshot,
    "runtime_snapshot_after": after_snapshot,
    "checks_passed_before_report": (
        checks_passed
    ),
}


REPORT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

REPORT_PATH.write_text(
    json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)


check(
    "Licensing implementation report was saved",
    (
        REPORT_PATH.exists()
        and REPORT_PATH.stat().st_size
        > 0
    ),
)


print()
print("=" * 92)

print(
    "MILESTONE 12.2B LICENCE AND "
    "THIRD-PARTY NOTICES: PASSED"
)

print("=" * 92)

print(
    "Checks passed:",
    checks_passed,
)

print(
    "Root project licence: Apache-2.0"
)

print(
    "Copyright holder: Swarup Bande"
)

print(
    "Application source files modified: NO"
)

print(
    "Private runtime data modified: NO"
)

print(
    "Model weights bundled: NO"
)

print(
    "FFmpeg executable bundled: NO"
)

print(
    "Services started: NO"
)

print()
print(
    "Report:",
    REPORT_PATH,
)
