from __future__ import annotations

from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent

START_PATH = (
    PROJECT_ROOT
    / "start_ai_voice_studio.ps1"
)

source = START_PATH.read_text(
    encoding="utf-8-sig"
)

state_marker = '''$state = [ordered]@{
'''

old_services_block = '''    services = [object[]](
        $serviceStates.ToArray()
    )
'''

new_services_block = '''    services = [object[]]$normalisedServiceStates
'''

old_final_loop = '''foreach ($serviceState in $serviceStates) {
'''

new_final_loop = '''foreach ($serviceState in $normalisedServiceStates) {
'''

ownership_marker = (
    "MANAGER OWNERSHIP PRESERVED"
)

if ownership_marker in source:
    raise RuntimeError(
        "Manager ownership preservation is already present."
    )

if source.count(
    state_marker
) != 1:
    raise RuntimeError(
        "Expected exactly one state creation block."
    )

if source.count(
    old_services_block
) != 1:
    raise RuntimeError(
        "Expected exactly one current services "
        "serialization block."
    )

if source.count(
    old_final_loop
) != 1:
    raise RuntimeError(
        "Expected exactly one final service summary loop."
    )

ownership_block = r'''# Preserve ownership when this manager previously started
# a service and a later invocation finds it already healthy.
$previousManagedServices = @{}

if (
    Test-Path `
        -LiteralPath $StatePath `
        -PathType Leaf
) {
    try {
        $previousStateJson = Get-Content `
            -LiteralPath $StatePath `
            -Raw

        $previousState = ConvertFrom-Json `
            -InputObject $previousStateJson

        foreach (
            $previousService in
            @($previousState.services)
        ) {
            if (
                [bool]$previousService.started_by_manager `
                -and $null -ne $previousService.process_id
            ) {
                $previousManagedServices[
                    [string]$previousService.name
                ] = $previousService
            }
        }
    }
    catch {
        Write-Warning (
            "Previous manager state could not be read. " +
            $_.Exception.Message
        )
    }
}

$normalisedServiceStates = @()

foreach (
    $serviceState in
    $serviceStates.ToArray()
) {
    $serviceName = [string]$serviceState.name

    if (
        -not [bool]$serviceState.started_by_manager `
        -and $previousManagedServices.ContainsKey(
            $serviceName
        )
    ) {
        $previousService = (
            $previousManagedServices[
                $serviceName
            ]
        )

        try {
            $previousProcessId = [int](
                $previousService.process_id
            )

            $null = Get-Process `
                -Id $previousProcessId `
                -ErrorAction Stop

            $serviceState.started_by_manager = $true
            $serviceState.process_id = $previousProcessId
            $serviceState.stdout_log = (
                $previousService.stdout_log
            )
            $serviceState.stderr_log = (
                $previousService.stderr_log
            )
            $serviceState.status = "already_running"

            Write-Host (
                $serviceName +
                ": MANAGER OWNERSHIP PRESERVED"
            ) -ForegroundColor Cyan
        }
        catch {
            Write-Warning (
                $serviceName +
                ": previous manager process " +
                "is no longer active."
            )
        }
    }

    $normalisedServiceStates += $serviceState
}

'''

source = source.replace(
    state_marker,
    ownership_block
    + state_marker,
    1,
)

source = source.replace(
    old_services_block,
    new_services_block,
    1,
)

source = source.replace(
    old_final_loop,
    new_final_loop,
    1,
)

required_markers = [
    "$previousManagedServices = @{}",
    "$previousState.services",
    "$previousService.process_id",
    "Get-Process",
    "MANAGER OWNERSHIP PRESERVED",
    "services = [object[]]$normalisedServiceStates",
    "foreach ($serviceState in $normalisedServiceStates)",
]

for marker in required_markers:
    if marker not in source:
        raise RuntimeError(
            "Patched startup manager is missing marker: "
            f"{marker}"
        )

START_PATH.write_text(
    source,
    encoding="utf-8",
)

print(
    "Milestone 11.1C-1 manager ownership "
    "preservation: APPLIED"
)
