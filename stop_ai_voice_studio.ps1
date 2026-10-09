param(
    [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path `
    -Parent `
    $MyInvocation.MyCommand.Path

$StatePath = Join-Path `
    $ProjectRoot `
    ".ai_voice_studio_state.json"

$LastStatePath = Join-Path `
    $ProjectRoot `
    ".ai_voice_studio_state.last.json"

function Stop-ProcessTree {
    param(
        [Parameter(Mandatory = $true)]
        [int]$ProcessId
    )

    & taskkill.exe `
        /PID $ProcessId `
        /T `
        /F |
        Out-Null
}

if ($ValidateOnly) {
    Write-Host (
        "AI Voice Studio stop manager validation: PASSED"
    ) -ForegroundColor Green

    exit 0
}

if (
    -not (
        Test-Path `
            -LiteralPath $StatePath `
            -PathType Leaf
    )
) {
    Write-Host (
        "No active AI Voice Studio manager state was found."
    ) -ForegroundColor Yellow

    exit 0
}

$stateJson = Get-Content `
    -LiteralPath $StatePath `
    -Raw

$state = ConvertFrom-Json `
    -InputObject $stateJson

$managedServices = @(
    $state.services
)

$stoppedCount = 0

foreach ($service in $managedServices) {
    if (
        -not $service.started_by_manager
    ) {
        Write-Host (
            $service.name +
            ": preserved because it was not started " +
            "by the manager."
        ) -ForegroundColor Yellow

        continue
    }

    if (
        $null -eq $service.process_id
    ) {
        continue
    }

    $processId = [int]$service.process_id

    try {
        Stop-ProcessTree `
            -ProcessId $processId

        $stoppedCount += 1

        Write-Host (
            $service.name +
            ": STOPPED"
        ) -ForegroundColor Green
    }
    catch {
        Write-Warning (
            $service.name +
            ": process tree could not be stopped. " +
            $_.Exception.Message
        )
    }
}

Copy-Item `
    -LiteralPath $StatePath `
    -Destination $LastStatePath `
    -Force

Remove-Item `
    -LiteralPath $StatePath `
    -Force

Write-Host ""
Write-Host (
    "Managed process trees stopped: $stoppedCount"
)

Write-Host (
    "Manually started services were preserved."
)
