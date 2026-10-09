# AI Voice Studio Privacy and Retention

## 1. Scope

This document describes the privacy and retention behaviour of the
current local AI Voice Studio release.

It does not claim that production privacy controls already exist.
Public deployment requires additional controls listed in this document.

## 2. Data processed by the application

Depending on user activity, AI Voice Studio may process:

- Reference voice recordings.
- Converted and trimmed WAV files.
- Voice names and language metadata.
- Whisper-generated transcripts.
- User-edited transcripts.
- Text submitted for speech generation.
- Generated speech files.
- Generation settings and engine metadata.
- Voice-style selections.
- Generation-history records.
- Error and service logs.

## 3. Current local storage

The current application stores data on the user's local machine.

Primary local locations include:

- `backend/app/voices/` for reference-voice files.
- `backend/app/outputs/` for generated audio.
- `backend/voice.db` for SQLite records.
- `logs/` for service output.
- `backend/milestone_backups/` for development backups.
- `backend/milestone_reports/` for engineering reports.

Personal voice files, generated audio, populated databases and logs are
excluded from the source release through `.gitignore` and release
packaging rules.

## 4. Local processing

The current architecture runs the main API, CosyVoice, IndicF5 and the
frontend as local services.

Package installation and model acquisition may contact external package
or model providers during setup. Those providers operate under their own
privacy notices and access terms.

Model weights are not included in the public source release.

## 5. Current retention behaviour

The current local release does not automatically expire voice files,
generated audio, database history, logs or development backups.

Data remains on the local machine until one of the following occurs:

- The user deletes it through the application.
- The operator removes it manually.
- A maintenance or release-cleanup process removes it.
- The local project directory is deleted.

This behaviour must be made visible to users before public deployment.

## 6. Deletion behaviour

The application supports deletion of saved voices and generated-output
history through its current product workflow.

Operators must also consider copies outside the primary application,
including:

- Downloaded audio.
- Manually copied files.
- Local backups.
- Service logs.
- Database backups.
- Cloud snapshots created by a future host.

A user-interface deletion cannot guarantee removal of copies that were
exported or separately backed up.

## 7. Data minimisation

Operators should collect only the minimum recording length and metadata
needed for reliable generation.

Reference recordings should avoid:

- Unrelated speakers.
- Private background conversations.
- Personal identifiers not required for synthesis.
- Sensitive information spoken accidentally.
- Excessively long source recordings.

Development tests should use authorised or synthetic test material.

## 8. Public-deployment retention gate

Before public deployment, the operator must define and implement:

- A default retention period for uploaded voices.
- A default retention period for generated audio.
- A retention period for operational logs.
- Account-level deletion.
- Deletion-request handling.
- Backup-deletion behaviour.
- Consent-record retention.
- Legal-hold handling where applicable.
- Storage-location disclosure.
- Provider and subprocessor disclosure where applicable.

The public privacy notice must state the actual configured periods. It
must not promise immediate deletion if backups retain data longer.

## 9. Security expectations

Public storage must use:

- Authentication and authorisation.
- Transport encryption.
- Restricted storage permissions.
- Secret management.
- Rate limits and abuse monitoring.
- Audit logging that avoids unnecessary voice content.
- Backup protection.
- Tested deletion procedures.

Encryption at rest is not claimed for the current local development
release.

## 10. User responsibilities

Users are responsible for:

- Uploading only authorised recordings.
- Protecting their local device.
- Deleting recordings that are no longer needed.
- Securing downloaded generated audio.
- Avoiding sensitive text that is unnecessary for generation.
- Following the Voice-Use Policy.

## 11. No sale or advertising claim

This local project documentation does not establish a business model,
advertising system or sale of personal data.

Any future operator must disclose its own actual data practices before
collecting data from public users.

## 12. Privacy review

Privacy controls must be reviewed whenever the project changes:

- Hosting provider.
- Storage provider.
- Authentication system.
- Analytics or monitoring.
- Model provider.
- Retention behaviour.
- Backup strategy.
- Public access level.

A useful risk-management reference is the NIST Privacy Framework:
https://www.nist.gov/privacy-framework

This document is technical privacy guidance and is not legal advice.
