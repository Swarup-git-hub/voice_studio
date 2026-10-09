# Security Policy

## Supported versions

AI Voice Studio is currently a local-first development project.

Security fixes are applied only to the latest maintained release and
the current default development branch. Older snapshots, milestone
backups and experimental copies are not supported.

## Reporting a vulnerability

Do not publish exploit details, credentials, private voice recordings
or reproduction data in a public issue.

For a public GitHub repository, use GitHub Private Vulnerability
Reporting through the repository's Security Advisories page.

If private reporting has not yet been enabled, create a public issue
requesting a private security contact, but do not include vulnerability
details in that issue.

Public deployment must not begin until the repository maintainer has
enabled a private reporting channel.

Official GitHub guidance:

- https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configuring-private-vulnerability-reporting-for-a-repository
- https://docs.github.com/en/code-security/concepts/vulnerability-reporting-and-management/coordinated-disclosure

## What to include in a private report

A useful report should include:

- Affected version or commit.
- Affected service and endpoint.
- Reproduction steps.
- Expected and observed behaviour.
- Security impact.
- Required privileges.
- Whether private voice or generated-audio data was accessed.
- Suggested mitigation where available.
- Whether the issue is already public.

Do not attach a real person's voice unless it is essential and you have
permission to share it. Prefer synthetic test audio.

## Coordinated disclosure

The maintainer will aim to:

1. Acknowledge the report.
2. Reproduce and classify the issue.
3. Develop and test a fix privately.
4. Inform affected users when necessary.
5. Publish an advisory after a fix is available.
6. Credit the reporter when requested and appropriate.

No fixed response-time guarantee is made for this personal project.

## Current security posture

The current release is intended for trusted local use.

It must not be exposed directly to the public internet in its current
form because public-production controls are not yet complete.

Current known deployment limitations include:

- No complete public-user authentication system.
- No production account and role model.
- No production rate limiting.
- No production abuse-detection workflow.
- No production consent registry.
- No hosted storage-retention enforcement.
- No claim of encryption at rest.
- No completed public privacy notice for a specific operator.
- No completed production backup and disaster-recovery policy.

These limitations are deployment blockers, not hidden features.

## Service exposure

The local services use:

- Frontend on port 5173.
- Main API on port 8000.
- CosyVoice service on port 8001.
- IndicF5 service on port 8002.

For local use, bind services only to trusted interfaces.

A production deployment must not expose internal model services
directly. Requests should pass through an authenticated application
API with validation, limits and monitoring.

## Secrets

Never commit:

- `.env` files.
- Access tokens.
- Model-provider credentials.
- Cloud credentials.
- Database passwords.
- Authentication secrets.
- Private keys.

Use environment variables or a managed secret store in production.

The committed `.env.example` must contain variable names and safe
examples only.

## Voice and audio data

Reference voices, transcripts and generated outputs must be treated as
sensitive information.

Security controls must prevent:

- Unauthorised file enumeration.
- Path traversal.
- Cross-user access.
- Guessable public download URLs.
- Unauthorised deletion.
- Log leakage.
- Backup leakage.
- Upload of dangerous or unsupported files.
- Use of another person's saved voice without permission.

## Upload security

A public deployment must enforce:

- File-size limits.
- Duration limits.
- Media-type verification.
- Safe generated filenames.
- Storage outside publicly executable directories.
- Audio decoding in a restricted process.
- Resource and concurrency limits.
- Cleanup of failed uploads.
- Malware and malformed-file handling appropriate to the host.

File extensions alone must not be treated as proof of file type.

## API security

Before public deployment, add and test:

- Authentication.
- Per-user authorisation.
- Rate limiting.
- Request-size limits.
- Timeouts.
- CORS restrictions.
- Secure cookies or token handling.
- Error responses that do not reveal internal paths.
- Audit events for sensitive changes.
- Protection against repeated expensive GPU requests.

## Dependency and model security

Dependencies and models must be obtained from known official sources.

Release maintenance must include:

- Dependency lock or reproducible version records.
- Vulnerability scanning.
- Review of licence and model-card changes.
- Model-file integrity checks where available.
- Exclusion of virtual environments and caches from releases.
- Exclusion of model weights from the source archive.
- Review before upgrading PyTorch, FFmpeg or model repositories.

The locally installed GPL-enabled FFmpeg executable is an external
prerequisite and is not included in the source release.

## Logging

Logs must not intentionally contain:

- Full reference-audio content.
- Secret values.
- Authentication tokens.
- Unnecessary transcript text.
- Private absolute file paths in public diagnostics.

Production logs require access controls and a documented retention
period.

## Incident response

If an incident may have exposed voice data:

1. Stop affected public access.
2. Preserve necessary evidence without spreading private data.
3. Rotate affected credentials.
4. Identify impacted users and files.
5. Correct the vulnerability.
6. Validate deletion or containment.
7. Notify affected parties when required.
8. Publish an advisory when disclosure is safe and appropriate.

## Release security gate

A public release must pass checks proving that it excludes:

- Personal reference voices.
- Generated output files.
- The populated local database.
- `.env` secrets.
- Logs.
- Virtual environments.
- `node_modules`.
- Internal milestone backups.
- Model weights.
- Local FFmpeg binaries.

This document describes project security expectations and is not a
guarantee that the software is free from vulnerabilities.
