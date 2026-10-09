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

start_marker = '''    if (
        Test-TcpListening `
            -Port $Port
    ) {
'''

end_marker = '''    $logTimestamp = Get-Date `
'''

start_count = source.count(
    start_marker
)

end_count = source.count(
    end_marker
)

if start_count != 1:
    raise RuntimeError(
        "Expected exactly one occupied-port block, "
        f"found {start_count}."
    )

if end_count != 1:
    raise RuntimeError(
        "Expected exactly one log-timestamp marker, "
        f"found {end_count}."
    )

block_start = source.index(
    start_marker
)

block_end = source.index(
    end_marker,
    block_start,
)

existing_block = source[
    block_start:block_end
]

required_existing_markers = [
    "$Name port $Port is occupied",
    "health endpoint is not healthy",
]

for marker in required_existing_markers:
    if marker not in existing_block:
        raise RuntimeError(
            "Occupied-port block is missing expected marker: "
            f"{marker}"
        )

replacement = '''    if (
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

'''

updated_source = (
    source[:block_start]
    + replacement
    + source[block_end:]
)

required_updated_markers = [
    "${Name}: PORT LISTENING; WAITING FOR HEALTH",
    "$graceSeconds = [Math]::Min(",
    "-TimeoutSeconds $graceSeconds",
    '"already_running"',
    "within $graceSeconds seconds",
]

for marker in required_updated_markers:
    if marker not in updated_source:
        raise RuntimeError(
            "Updated startup manager is missing marker: "
            f"{marker}"
        )

if updated_source.count(
    "${Name}: PORT LISTENING; WAITING FOR HEALTH"
) != 1:
    raise RuntimeError(
        "Health grace-period block was inserted incorrectly."
    )

START_PATH.write_text(
    updated_source,
    encoding="utf-8",
)

print(
    "Milestone 11.1B occupied-port health "
    "grace period: APPLIED"
)
