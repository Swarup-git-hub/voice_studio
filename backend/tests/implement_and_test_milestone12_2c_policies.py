from __future__ import annotations

import json
import os
import re
import socket
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(
    os.environ[
        "MILESTONE12_2C_PROJECT_ROOT"
    ]
).resolve()

BACKEND_ROOT = (
    PROJECT_ROOT
    / "backend"
)

VOICE_POLICY_PATH = (
    PROJECT_ROOT
    / "VOICE_USE_POLICY.md"
)

PRIVACY_PATH = (
    PROJECT_ROOT
    / "PRIVACY_AND_RETENTION.md"
)

SECURITY_PATH = (
    PROJECT_ROOT
    / "SECURITY.md"
)

REPORT_PATH = Path(
    os.environ[
        "MILESTONE12_2C_REPORT_PATH"
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
        "milestone_backups": (
            BACKEND_ROOT
            / "milestone_backups"
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

                try:
                    file_count += 1
                    total_bytes += path.stat().st_size

                except OSError:
                    continue

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
    source: str,
) -> bool:
    return (
        re.search(
            r"(?m)^[A-Za-z]:[\\/]",
            source,
        )
        is not None
    )


def contains_normalized_marker(
    source: str,
    marker: str,
) -> bool:
    normalized_source = " ".join(
        source.split()
    )

    normalized_marker = " ".join(
        marker.split()
    )

    return normalized_marker in normalized_source


print("=" * 92)
print(
    "MILESTONE 12.2C — VOICE-USE, "
    "PRIVACY AND SECURITY POLICIES"
)
print("=" * 92)


before_snapshot = runtime_snapshot()


VOICE_POLICY_PATH.write_text(
    """# AI Voice Studio Voice-Use Policy

## 1. Purpose

AI Voice Studio creates synthetic speech from text and a reference
voice. Voice cloning can provide legitimate creative, accessibility,
localisation and educational benefits, but it can also be misused for
impersonation, fraud, harassment or deceptive attribution.

This policy applies to anyone who uploads, stores, clones or generates
audio with AI Voice Studio.

## 2. Required authority and consent

A user may upload or clone a voice only when at least one of the
following is true:

1. The voice belongs to the user and the user owns or controls the
   reference recording.
2. The speaker has given explicit, informed permission for both the
   recording and synthetic voice generation.
3. The user has documented legal authority to act for the speaker.

Permission to possess, stream or view a recording does not by itself
grant permission to create a synthetic version of the speaker's voice.

Public availability of a podcast, interview, video, broadcast or social
media recording does not by itself establish voice-cloning consent.

## 3. Consent standard

For public, organisational or commercial use, the operator should keep
a consent record that identifies:

- The speaker.
- The person or organisation receiving permission.
- The intended use.
- Whether commercial use is allowed.
- Whether sharing or publication is allowed.
- The date consent was given.
- Any limits or expiry conditions.
- A process for withdrawal where applicable.

The current local release does not yet implement an electronic consent
registry. Public deployment is blocked until an appropriate consent
confirmation and audit record are implemented.

## 4. Children and protected persons

Do not clone the voice of a child or a person who cannot provide
informed consent unless the operator has verified appropriate guardian
or legal authority and complies with applicable law.

Extra care is required when a speaker may be vulnerable, dependent on
another person or unable to understand the proposed use.

## 5. Public figures and third parties

Being a public figure does not remove the need for permission.

Do not create synthetic endorsements, announcements, political
statements, emergency messages or commercial promotions that falsely
appear to come from another person.

## 6. Prohibited uses

AI Voice Studio must not be used for:

- Fraud, extortion, scams or identity deception.
- Bypassing voice-authentication systems.
- Impersonating another person without authority.
- Fabricating evidence or official communications.
- Deceptive political or commercial endorsements.
- Harassment, bullying, threats or targeted abuse.
- Defamation or deliberate reputational harm.
- Non-consensual sexual or exploitative content.
- Misleading medical, financial, legal or emergency instructions.
- Circumventing another platform's safety or access controls.
- Concealing the synthetic nature of audio when that omission could
  reasonably mislead a listener.

## 7. Disclosure

Synthetic audio should be clearly identified as AI-generated or
synthetic when listeners could otherwise reasonably believe that it is
an authentic recording of the speaker.

The current local release does not automatically watermark generated
audio. Operators are responsible for adding suitable disclosure before
publication.

Watermarking or provenance metadata should be evaluated before public
deployment.

## 8. Storage and deletion

Reference voices, transcripts and generated audio should be treated as
sensitive information.

Users should:

- Store only recordings required for the intended purpose.
- Avoid uploading unrelated conversation or background speech.
- Delete obsolete reference voices and generated files.
- Protect backups and exported audio.
- Avoid sharing generated content beyond the permission granted.

The application must preserve functional deletion of saved voices and
generated outputs.

## 9. Operator responsibilities

A person or organisation deploying AI Voice Studio is responsible for:

- Verifying consent.
- Restricting access.
- Protecting stored recordings.
- Publishing clear retention rules.
- Handling deletion and withdrawal requests.
- Monitoring misuse.
- Suspending abusive users.
- Complying with applicable laws and model-provider terms.

## 10. Enforcement

Access may be refused, suspended or terminated when use violates this
policy.

Generated files and reference voices associated with confirmed misuse
may be removed where legally and technically appropriate.

## 11. No transfer of identity rights

The Apache-2.0 project licence covers eligible project code. It does
not grant permission to use a person's voice, name, likeness, identity,
performance or endorsement.

Model licences also do not replace speaker consent.

## 12. References

Responsible deployment should consider current official guidance,
including:

- FTC Voice Cloning Challenge:
  https://www.ftc.gov/news-events/contests/ftc-voice-cloning-challenge
- FTC approaches to AI-enabled voice cloning:
  https://www.ftc.gov/policy/advocacy-research/tech-at-ftc/2024/04/approaches-address-ai-enabled-voice-cloning

This policy is project guidance and is not legal advice.
""",
    encoding="utf-8",
)


PRIVACY_PATH.write_text(
    """# AI Voice Studio Privacy and Retention

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
""",
    encoding="utf-8",
)


SECURITY_PATH.write_text(
    """# Security Policy

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
""",
    encoding="utf-8",
)


after_snapshot = runtime_snapshot()


check(
    "Voice-use policy was created",
    VOICE_POLICY_PATH.exists(),
)

voice_policy = (
    VOICE_POLICY_PATH.read_text(
        encoding="utf-8"
    )
)


for name, marker in {
    "Explicit voice permission requirement": (
        "explicit, informed permission"
    ),
    "Public recordings do not imply consent": (
        "Public availability"
    ),
    "Public-figure protection": (
        "Being a public figure"
    ),
    "Fraud prohibition": (
        "Fraud, extortion, scams"
    ),
    "Voice-authentication bypass prohibition": (
        "Bypassing voice-authentication"
    ),
    "Synthetic-audio disclosure": (
        "Synthetic audio should be clearly identified"
    ),
    "Consent registry deployment gate": (
        "does not yet implement an electronic consent"
    ),
    "Software licence identity separation": (
        "permission to use a person's voice"
    ),
}.items():
    check(
        name,
        contains_normalized_marker(
            voice_policy,
            marker,
        ),
        marker,
    )


check(
    "Privacy and retention document was created",
    PRIVACY_PATH.exists(),
)

privacy_source = (
    PRIVACY_PATH.read_text(
        encoding="utf-8"
    )
)


for name, marker in {
    "Current local storage is documented": (
        "stores data on the user's local machine"
    ),
    "Voice storage path is documented": (
        "`backend/app/voices/`"
    ),
    "Output storage path is documented": (
        "`backend/app/outputs/`"
    ),
    "SQLite storage is documented": (
        "`backend/voice.db`"
    ),
    "No automatic expiry is disclosed": (
        "does not automatically expire"
    ),
    "Backup deletion limitation is disclosed": (
        "cannot guarantee removal of copies"
    ),
    "Data minimisation is documented": (
        "minimum recording length and metadata"
    ),
    "Public retention gate is documented": (
        "default retention period"
    ),
    "Encryption at rest is not overclaimed": (
        "Encryption at rest is not claimed"
    ),
}.items():
    check(
        name,
        contains_normalized_marker(
            privacy_source,
            marker,
        ),
        marker,
    )


check(
    "Security policy was created",
    SECURITY_PATH.exists(),
)

security_source = (
    SECURITY_PATH.read_text(
        encoding="utf-8"
    )
)


for name, marker in {
    "Supported-version policy is documented": (
        "latest maintained release"
    ),
    "Private reporting is required": (
        "Private Vulnerability Reporting"
    ),
    "Public exploit disclosure is prohibited": (
        "Do not publish exploit details"
    ),
    "Current local-only posture is disclosed": (
        "intended for trusted local use"
    ),
    "Public exposure is blocked": (
        "must not be exposed directly to the public internet"
    ),
    "Authentication limitation is disclosed": (
        "No complete public-user authentication system"
    ),
    "Secrets protection is documented": (
        "Never commit:"
    ),
    "Cross-user voice access risk is documented": (
        "Cross-user access"
    ),
    "Upload validation is documented": (
        "Media-type verification"
    ),
    "Rate limiting requirement is documented": (
        "Rate limiting"
    ),
    "Model service isolation is documented": (
        "must not expose internal model services directly"
    ),
    "Incident response is documented": (
        "If an incident may have exposed voice data"
    ),
}.items():
    check(
        name,
        contains_normalized_marker(
            security_source,
            marker,
        ),
        marker,
    )


release_documents = {
    "VOICE_USE_POLICY.md": voice_policy,
    "PRIVACY_AND_RETENTION.md": (
        privacy_source
    ),
    "SECURITY.md": security_source,
}


unsafe_path_documents = {
    name: True
    for name, source in release_documents.items()
    if contains_windows_absolute_path(
        source
    )
}


check(
    "Policy documents contain no personal Windows paths",
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
    "milestone": "12.2C",
    "created_at": datetime.now().isoformat(),
    "application_source_files_modified": False,
    "private_runtime_data_modified": False,
    "services_started": False,
    "documents_created": [
        str(
            VOICE_POLICY_PATH
        ),
        str(
            PRIVACY_PATH
        ),
        str(
            SECURITY_PATH
        ),
    ],
    "policy_scope": {
        "voice_consent": True,
        "prohibited_misuse": True,
        "synthetic_disclosure": True,
        "privacy_and_retention": True,
        "security_reporting": True,
        "public_deployment_gates": True,
    },
    "current_public_deployment_approved": False,
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
    "Policy implementation report was saved",
    (
        REPORT_PATH.exists()
        and REPORT_PATH.stat().st_size
        > 0
    ),
)


print()
print("=" * 92)

print(
    "MILESTONE 12.2C VOICE, PRIVACY "
    "AND SECURITY POLICIES: PASSED"
)

print("=" * 92)

print(
    "Checks passed:",
    checks_passed,
)

print(
    "Voice-use policy: CREATED"
)

print(
    "Privacy and retention policy: CREATED"
)

print(
    "Security policy: CREATED"
)

print(
    "Public deployment approved: NO"
)

print(
    "Application source files modified: NO"
)

print(
    "Private runtime data modified: NO"
)

print(
    "Services started: NO"
)

print()
print(
    "Report:",
    REPORT_PATH,
)
