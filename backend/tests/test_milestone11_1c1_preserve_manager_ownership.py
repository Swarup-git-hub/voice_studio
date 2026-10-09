from __future__ import annotations

from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent

START_PATH = (
    PROJECT_ROOT
    / "start_ai_voice_studio.ps1"
)


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


print("=" * 92)
print(
    "MILESTONE 11.1C-1 — PRESERVE "
    "STARTUP-MANAGER OWNERSHIP"
)
print("=" * 92)

check(
    "Startup manager exists",
    START_PATH.exists(),
    str(
        START_PATH
    ),
)

source = START_PATH.read_text(
    encoding="utf-8-sig"
)

required_markers = [
    "$previousManagedServices = @{}",
    "$previousState.services",
    "$previousService.process_id",
    "Get-Process",
    "$serviceState.started_by_manager = $true",
    "$serviceState.process_id = $previousProcessId",
    "$serviceState.stdout_log",
    "$serviceState.stderr_log",
    "MANAGER OWNERSHIP PRESERVED",
    "services = [object[]]$normalisedServiceStates",
    "foreach ($serviceState in $normalisedServiceStates)",
]

for marker in required_markers:
    check(
        f"Startup manager contains {marker}",
        marker in source,
    )

check(
    "Ownership block appears exactly once",
    source.count(
        "MANAGER OWNERSHIP PRESERVED"
    )
    == 1,
)

check(
    "State uses normalised service ownership",
    source.count(
        "services = [object[]]$normalisedServiceStates"
    )
    == 1,
)

check(
    "Old generic-list state block is absent",
    '''services = [object[]](
        $serviceStates.ToArray()
    )'''
    not in source,
)

print()
print("=" * 92)
print(
    "MILESTONE 11.1C-1 MANAGER OWNERSHIP "
    "PRESERVATION: PASSED"
)
print("=" * 92)

print(
    "Checks passed:",
    checks_passed,
)
