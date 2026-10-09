from __future__ import annotations

from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent

START_PATH = (
    PROJECT_ROOT
    / "start_ai_voice_studio.ps1"
)

STOP_PATH = (
    PROJECT_ROOT
    / "stop_ai_voice_studio.ps1"
)

TEST_PATH = (
    BACKEND_ROOT
    / "tests"
    / "test_milestone11_1b_startup_manager.py"
)


START_SCRIPT = r'''param(
    [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path `
    -Parent `
    $MyInvocation.MyCommand.Path

$BackendRoot = Join-Path `
    $ProjectRoot `
    "backend"

$FrontendRoot = Join-Path `
    $ProjectRoot `
    "frontend"

$CosyVoiceRoot = Join-Path `
    $BackendRoot `
    "ai_models\cosyvoice"

$RootPython = Join-Path `
    $ProjectRoot `
    ".venv\Scripts\python.exe"

$IndicF5Python = Join-Path `
    $ProjectRoot `
    "indicf5_env\Scripts\python.exe"

$CosyVoicePython = Join-Path `
    $ProjectRoot `
    "cosyvoice_env\Scripts\python.exe"

$StatePath = Join-Path `
    $ProjectRoot `
    ".ai_voice_studio_state.json"

$LogRoot = Join-Path `
    $ProjectRoot `
    "logs\local_services"

function Test-HttpHealthy {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url
    )

    try {
        $response = Invoke-WebRequest `
            -Uri $Url `
            -UseBasicParsing `
            -TimeoutSec 5 `
            -ErrorAction Stop

        return (
            [int]$response.StatusCode -ge 200 `
            -and [int]$response.StatusCode -lt 400
        )
    }
    catch {
        return $false
    }
}

function Test-TcpListening {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    return [bool](
        Test-NetConnection `
            -ComputerName "127.0.0.1" `
            -Port $Port `
            -InformationLevel Quiet `
            -WarningAction SilentlyContinue
    )
}

function Wait-ForHealth {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,

        [Parameter(Mandatory = $true)]
        [int]$TimeoutSeconds
    )

    $deadline = (
        Get-Date
    ).AddSeconds(
        $TimeoutSeconds
    )

    while (
        (Get-Date) -lt $deadline
    ) {
        if (
            Test-HttpHealthy `
                -Url $Url
        ) {
            return $true
        }

        Start-Sleep `
            -Seconds 2
    }

    return $false
}

function Stop-ProcessTree {
    param(
        [Parameter(Mandatory = $true)]
        [int]$ProcessId
    )

    try {
        & taskkill.exe `
            /PID $ProcessId `
            /T `
            /F |
            Out-Null
    }
    catch {
        Write-Warning (
            "Unable to stop process tree " +
            "$ProcessId."
        )
    }
}

function Start-ManagedService {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [string]$Executable,

        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,

        [Parameter(Mandatory = $true)]
        [string]$WorkingDirectory,

        [Parameter(Mandatory = $true)]
        [string]$HealthUrl,

        [Parameter(Mandatory = $true)]
        [int]$Port,

        [Parameter(Mandatory = $true)]
        [int]$TimeoutSeconds,

        [Parameter(Mandatory = $true)]
        [string]$LogPrefix
    )

    if (
        Test-HttpHealthy `
            -Url $HealthUrl
    ) {
        Write-Host (
            "$Name: ALREADY HEALTHY"
        ) -ForegroundColor Yellow

        return [pscustomobject]@{
            name = $Name
            port = $Port
            health_url = $HealthUrl
            status = "already_running"
            started_by_manager = $false
            process_id = $null
            stdout_log = $null
            stderr_log = $null
        }
    }

    if (
        Test-TcpListening `
            -Port $Port
    ) {
        throw (
            "$Name port $Port is occupied, " +
            "but its health endpoint is not healthy."
        )
    }

    $logTimestamp = Get-Date `
        -Format "yyyyMMdd_HHmmss"

    $stdoutLog = Join-Path `
        $LogRoot `
        ($LogPrefix + "_" + $logTimestamp + ".stdout.log")

    $stderrLog = Join-Path `
        $LogRoot `
        ($LogPrefix + "_" + $logTimestamp + ".stderr.log")

    Write-Host (
        "$Name: STARTING"
    ) -ForegroundColor Cyan

    $process = Start-Process `
        -FilePath $Executable `
        -ArgumentList $Arguments `
        -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -WindowStyle Hidden `
        -PassThru

    if (
        -not (
            Wait-ForHealth `
                -Url $HealthUrl `
                -TimeoutSeconds $TimeoutSeconds
        )
    ) {
        Stop-ProcessTree `
            -ProcessId $process.Id

        throw (
            "$Name failed its health check within " +
            "$TimeoutSeconds seconds.`n" +
            "Standard output: $stdoutLog`n" +
            "Standard error: $stderrLog"
        )
    }

    Write-Host (
        "$Name: HEALTHY"
    ) -ForegroundColor Green

    return [pscustomobject]@{
        name = $Name
        port = $Port
        health_url = $HealthUrl
        status = "started"
        started_by_manager = $true
        process_id = $process.Id
        stdout_log = $stdoutLog
        stderr_log = $stderrLog
    }
}

$requiredDirectories = @(
    $BackendRoot,
    $FrontendRoot,
    $CosyVoiceRoot
)

foreach ($directory in $requiredDirectories) {
    if (
        -not (
            Test-Path `
                -LiteralPath $directory `
                -PathType Container
        )
    ) {
        throw (
            "Required directory is missing: " +
            $directory
        )
    }
}

$requiredExecutables = @(
    $RootPython,
    $IndicF5Python,
    $CosyVoicePython
)

foreach ($executable in $requiredExecutables) {
    if (
        -not (
            Test-Path `
                -LiteralPath $executable `
                -PathType Leaf
        )
    ) {
        throw (
            "Required executable is missing: " +
            $executable
        )
    }
}

$npmCommand = Get-Command `
    "npm.cmd" `
    -ErrorAction Stop

$NpmPath = $npmCommand.Source

if ($ValidateOnly) {
    Write-Host (
        "AI Voice Studio startup manager validation: PASSED"
    ) -ForegroundColor Green

    Write-Host (
        "Root Python: $RootPython"
    )

    Write-Host (
        "IndicF5 Python: $IndicF5Python"
    )

    Write-Host (
        "CosyVoice Python: $CosyVoicePython"
    )

    Write-Host (
        "npm.cmd: $NpmPath"
    )

    exit 0
}

New-Item `
    -ItemType Directory `
    -Path $LogRoot `
    -Force |
    Out-Null

$serviceStates = New-Object `
    System.Collections.Generic.List[object]

$startedProcessIds = New-Object `
    System.Collections.Generic.List[int]

try {
    $cosyVoiceState = Start-ManagedService `
        -Name "CosyVoice" `
        -Executable $CosyVoicePython `
        -Arguments @(
            "-m",
            "uvicorn",
            "server:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8001"
        ) `
        -WorkingDirectory $CosyVoiceRoot `
        -HealthUrl "http://127.0.0.1:8001/health" `
        -Port 8001 `
        -TimeoutSeconds 420 `
        -LogPrefix "cosyvoice"

    $serviceStates.Add(
        $cosyVoiceState
    )

    if (
        $cosyVoiceState.started_by_manager
    ) {
        $startedProcessIds.Add(
            [int]$cosyVoiceState.process_id
        )
    }

    $indicF5State = Start-ManagedService `
        -Name "IndicF5" `
        -Executable $IndicF5Python `
        -Arguments @(
            "-m",
            "uvicorn",
            "ai_models.indicf5.server:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8002",
            "--workers",
            "1"
        ) `
        -WorkingDirectory $BackendRoot `
        -HealthUrl "http://127.0.0.1:8002/health" `
        -Port 8002 `
        -TimeoutSeconds 420 `
        -LogPrefix "indicf5"

    $serviceStates.Add(
        $indicF5State
    )

    if (
        $indicF5State.started_by_manager
    ) {
        $startedProcessIds.Add(
            [int]$indicF5State.process_id
        )
    }

    $backendState = Start-ManagedService `
        -Name "FastAPI backend" `
        -Executable $RootPython `
        -Arguments @(
            "-m",
            "uvicorn",
            "app.main:app",
            "--reload",
            "--port",
            "8000"
        ) `
        -WorkingDirectory $BackendRoot `
        -HealthUrl "http://127.0.0.1:8000/health" `
        -Port 8000 `
        -TimeoutSeconds 120 `
        -LogPrefix "backend"

    $serviceStates.Add(
        $backendState
    )

    if (
        $backendState.started_by_manager
    ) {
        $startedProcessIds.Add(
            [int]$backendState.process_id
        )
    }

    $frontendState = Start-ManagedService `
        -Name "Frontend" `
        -Executable $NpmPath `
        -Arguments @(
            "run",
            "dev",
            "--",
            "--host",
            "127.0.0.1",
            "--port",
            "5173"
        ) `
        -WorkingDirectory $FrontendRoot `
        -HealthUrl "http://127.0.0.1:5173" `
        -Port 5173 `
        -TimeoutSeconds 90 `
        -LogPrefix "frontend"

    $serviceStates.Add(
        $frontendState
    )

    if (
        $frontendState.started_by_manager
    ) {
        $startedProcessIds.Add(
            [int]$frontendState.process_id
        )
    }
}
catch {
    foreach (
        $startedProcessId in
        $startedProcessIds
    ) {
        Stop-ProcessTree `
            -ProcessId $startedProcessId
    }

    throw
}

$state = [ordered]@{
    version = 1
    created_at = (
        Get-Date
    ).ToString("o")
    project_root = $ProjectRoot
    services = @(
        $serviceStates
    )
}

$state |
    ConvertTo-Json `
        -Depth 6 |
    Set-Content `
        -LiteralPath $StatePath `
        -Encoding UTF8

Write-Host ""
Write-Host (
    "AI Voice Studio local services: HEALTHY"
) -ForegroundColor Green

Write-Host (
    "State file: $StatePath"
)

Write-Host (
    "Log folder: $LogRoot"
)

Write-Host ""

foreach ($serviceState in $serviceStates) {
    Write-Host (
        $serviceState.name +
        " = " +
        $serviceState.status
    )
}
'''


STOP_SCRIPT = r'''param(
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
'''


TEST_SCRIPT = r'''from __future__ import annotations

import json
import socket
import urllib.request
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent

START_PATH = (
    PROJECT_ROOT
    / "start_ai_voice_studio.ps1"
)

STOP_PATH = (
    PROJECT_ROOT
    / "stop_ai_voice_studio.ps1"
)

STATE_PATH = (
    PROJECT_ROOT
    / ".ai_voice_studio_state.json"
)

LOG_ROOT = (
    PROJECT_ROOT
    / "logs"
    / "local_services"
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


def tcp_open(
    port: int,
) -> bool:
    try:
        with socket.create_connection(
            (
                "127.0.0.1",
                port,
            ),
            timeout=3,
        ):
            return True

    except OSError:
        return False


def http_healthy(
    url: str,
) -> bool:
    try:
        with urllib.request.urlopen(
            url,
            timeout=15,
        ) as response:
            status = int(
                response.getcode()
                or 200
            )

            return (
                200
                <= status
                < 400
            )

    except Exception:
        return False


print("=" * 92)
print(
    "MILESTONE 11.1B — IDEMPOTENT LOCAL "
    "STARTUP MANAGER"
)
print("=" * 92)

check(
    "Startup script exists",
    START_PATH.exists(),
    str(
        START_PATH
    ),
)

check(
    "Stop script exists",
    STOP_PATH.exists(),
    str(
        STOP_PATH
    ),
)

check(
    "Startup state file exists",
    STATE_PATH.exists(),
    str(
        STATE_PATH
    ),
)

check(
    "Local service log folder exists",
    LOG_ROOT.exists(),
    str(
        LOG_ROOT
    ),
)

state: dict[str, Any] = json.loads(
    STATE_PATH.read_text(
        encoding="utf-8-sig",
    )
)

services = state.get(
    "services"
)

check(
    "State contains four services",
    (
        isinstance(
            services,
            list,
        )
        and len(
            services
        )
        == 4
    ),
    repr(
        services
    ),
)

expected_names = {
    "CosyVoice",
    "IndicF5",
    "FastAPI backend",
    "Frontend",
}

actual_names = {
    item.get(
        "name"
    )
    for item in services
}

check(
    "State contains the expected services",
    actual_names
    == expected_names,
    repr(
        actual_names
    ),
)

allowed_statuses = {
    "already_running",
    "started",
}

check(
    "Every service has a valid startup status",
    all(
        item.get(
            "status"
        )
        in allowed_statuses
        for item in services
    ),
    repr(
        services
    ),
)

service_contracts = [
    (
        "Frontend",
        5173,
        "http://127.0.0.1:5173",
    ),
    (
        "FastAPI backend",
        8000,
        "http://127.0.0.1:8000/health",
    ),
    (
        "CosyVoice",
        8001,
        "http://127.0.0.1:8001/health",
    ),
    (
        "IndicF5",
        8002,
        "http://127.0.0.1:8002/health",
    ),
]

for service_name, port, health_url in (
    service_contracts
):
    check(
        f"{service_name} TCP port is listening",
        tcp_open(
            port
        ),
        str(
            port
        ),
    )

    check(
        f"{service_name} HTTP health is ready",
        http_healthy(
            health_url
        ),
        health_url,
    )

print()
print("Service startup state:")

for item in services:
    print(
        " ",
        item.get(
            "name"
        ),
        "=",
        item.get(
            "status"
        ),
    )

print()
print("=" * 92)
print(
    "MILESTONE 11.1B IDEMPOTENT LOCAL "
    "STARTUP MANAGER: PASSED"
)
print("=" * 92)

print(
    "Checks passed:",
    checks_passed,
)
'''


START_PATH.write_text(
    START_SCRIPT,
    encoding="utf-8",
)

STOP_PATH.write_text(
    STOP_SCRIPT,
    encoding="utf-8",
)

TEST_PATH.write_text(
    TEST_SCRIPT,
    encoding="utf-8",
)

print(
    "Milestone 11.1B startup manager files: CREATED"
)
