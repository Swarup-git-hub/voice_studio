# Third-Party Notices

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
