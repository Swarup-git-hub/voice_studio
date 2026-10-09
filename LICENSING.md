# AI Voice Studio Licensing

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
