# Model, Dataset and Voice Terms

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
