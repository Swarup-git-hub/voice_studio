param(
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
            "${Name}: ALREADY HEALTHY"
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
        $graceSeconds = [Math]::Min(
            $TimeoutSeconds,
            45
        )

        Write-Host (
            "${Name}: PORT LISTENING; WAITING FOR HEALTH"
        ) -ForegroundColor Yellow

        if (
            Wait-ForHealth `
                -Url $HealthUrl `
                -TimeoutSeconds $graceSeconds
        ) {
            Write-Host (
                "${Name}: ALREADY HEALTHY"
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

        throw (
            "$Name port $Port is occupied, " +
            "but its health endpoint did not become healthy " +
            "within $graceSeconds seconds."
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
        "${Name}: STARTING"
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
        "${Name}: HEALTHY"
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

# Preserve ownership when this manager previously started
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

$state = [ordered]@{
    version = 1
    created_at = (
        Get-Date
    ).ToString("o")
    project_root = $ProjectRoot
    services = [object[]]$normalisedServiceStates
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

foreach ($serviceState in $normalisedServiceStates) {
    Write-Host (
        $serviceState.name +
        " = " +
        $serviceState.status
    )
}
