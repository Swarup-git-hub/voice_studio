from __future__ import annotations

import csv
import io
import json
import socket
import subprocess
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Callable


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

LAST_STATE_PATH = (
    PROJECT_ROOT
    / ".ai_voice_studio_state.last.json"
)

REPORT_ROOT = (
    BACKEND_ROOT
    / "milestone_reports"
)

TIMESTAMP = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

SNAPSHOT_PATH = (
    REPORT_ROOT
    / f"milestone11_1c2_first_start_state_{TIMESTAMP}.json"
)

REPORT_PATH = (
    REPORT_ROOT
    / f"milestone11_1c2_cold_start_shutdown_{TIMESTAMP}.json"
)


SERVICE_CONTRACTS = {
    "Frontend": {
        "port": 5173,
        "health_url": "http://127.0.0.1:5173",
    },
    "FastAPI backend": {
        "port": 8000,
        "health_url": "http://127.0.0.1:8000/health",
    },
    "CosyVoice": {
        "port": 8001,
        "health_url": "http://127.0.0.1:8001/health",
    },
    "IndicF5": {
        "port": 8002,
        "health_url": "http://127.0.0.1:8002/health",
    },
}


checks_passed = 0

manager_started = False
shutdown_completed = False


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


def run_manager(
    script_path: Path,
    *arguments: str,
) -> str:
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(
            script_path
        ),
        *arguments,
    ]

    validate_only = (
        "-ValidateOnly"
        in arguments
    )

    if validate_only:
        timeout_seconds = 120

    elif script_path == START_PATH:
        timeout_seconds = 1200

    else:
        timeout_seconds = 300

    manager_log_root = (
        REPORT_ROOT
        / "manager_command_logs"
    )

    manager_log_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    argument_label = (
        "validate"
        if validate_only
        else "execute"
    )

    log_prefix = (
        script_path.stem
        + "_"
        + argument_label
        + "_"
        + run_timestamp
    )

    stdout_path = (
        manager_log_root
        / f"{log_prefix}.stdout.log"
    )

    stderr_path = (
        manager_log_root
        / f"{log_prefix}.stderr.log"
    )

    print()
    print(
        "Running manager command:",
        " ".join(
            command
        ),
    )

    print(
        "Manager stdout log:",
        stdout_path,
    )

    print(
        "Manager stderr log:",
        stderr_path,
    )

    print(
        "Manager timeout:",
        timeout_seconds,
        "seconds",
    )

    print(
        flush=True
    )

    with stdout_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stdout_file, stderr_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stderr_file:
        process = subprocess.Popen(
            command,
            cwd=str(
                PROJECT_ROOT
            ),
            stdout=stdout_file,
            stderr=stderr_file,
            text=True,
        )

        started_at = time.monotonic()
        next_heartbeat = (
            started_at
            + 15
        )

        while True:
            return_code = process.poll()

            if return_code is not None:
                break

            now = time.monotonic()
            elapsed_seconds = (
                now
                - started_at
            )

            if elapsed_seconds >= timeout_seconds:
                termination = subprocess.run(
                    [
                        "taskkill.exe",
                        "/PID",
                        str(
                            process.pid
                        ),
                        "/T",
                        "/F",
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    errors="replace",
                    check=False,
                )

                try:
                    process.wait(
                        timeout=30
                    )

                except subprocess.TimeoutExpired:
                    pass

                stdout_file.flush()
                stderr_file.flush()

                stdout_text = stdout_path.read_text(
                    encoding="utf-8",
                    errors="replace",
                )

                stderr_text = stderr_path.read_text(
                    encoding="utf-8",
                    errors="replace",
                )

                raise TimeoutError(
                    "Manager command exceeded its timeout.\n"
                    f"Command: {command}\n"
                    f"Timeout: {timeout_seconds} seconds\n"
                    f"taskkill stdout:\n{termination.stdout}\n"
                    f"taskkill stderr:\n{termination.stderr}\n"
                    f"Manager stdout:\n{stdout_text}\n"
                    f"Manager stderr:\n{stderr_text}"
                )

            if now >= next_heartbeat:
                port_summary = ", ".join(
                    (
                        f"{name}="
                        f"{tcp_open(int(contract['port']))}"
                    )
                    for name, contract
                    in SERVICE_CONTRACTS.items()
                )

                print(
                    "Manager still running after "
                    f"{elapsed_seconds:.0f}s | "
                    f"TCP ports: {port_summary}",
                    flush=True,
                )

                next_heartbeat = (
                    now
                    + 15
                )

            time.sleep(
                1
            )

        return_code = int(
            process.returncode
            if process.returncode
            is not None
            else -1
        )

    stdout_text = stdout_path.read_text(
        encoding="utf-8",
        errors="replace",
    ).rstrip()

    stderr_text = stderr_path.read_text(
        encoding="utf-8",
        errors="replace",
    ).rstrip()

    output_parts = []

    if stdout_text:
        output_parts.append(
            stdout_text
        )

    if stderr_text:
        output_parts.append(
            stderr_text
        )

    combined_output = "\n".join(
        output_parts
    )

    if combined_output:
        print()
        print(
            combined_output
        )
        print()

    if return_code != 0:
        raise RuntimeError(
            "Manager command failed.\n"
            f"Command: {command}\n"
            f"Exit code: {return_code}\n"
            f"Standard output log: {stdout_path}\n"
            f"Standard error log: {stderr_path}\n"
            f"Output:\n{combined_output}"
        )

    return combined_output



def tcp_open(
    port: int,
) -> bool:
    try:
        with socket.create_connection(
            (
                "127.0.0.1",
                port,
            ),
            timeout=2.0,
        ):
            return True

    except OSError:
        return False


def http_healthy(
    url: str,
) -> bool:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "AI-Voice-Studio-Milestone-11.1C-2"
            ),
        },
    )

    try:
        with urllib.request.urlopen(
            request,
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


def wait_until(
    condition: Callable[[], bool],
    *,
    timeout_seconds: float,
    interval_seconds: float = 1.0,
) -> bool:
    deadline = (
        time.monotonic()
        + timeout_seconds
    )

    while (
        time.monotonic()
        < deadline
    ):
        if condition():
            return True

        time.sleep(
            interval_seconds
        )

    return condition()


def process_alive(
    process_id: int,
) -> bool:
    completed = subprocess.run(
        [
            "tasklist.exe",
            "/FI",
            f"PID eq {process_id}",
            "/FO",
            "CSV",
            "/NH",
        ],
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )

    if completed.returncode != 0:
        return False

    rows = csv.reader(
        io.StringIO(
            completed.stdout
        )
    )

    for row in rows:
        if len(
            row
        ) < 2:
            continue

        try:
            returned_pid = int(
                row[1]
            )

        except ValueError:
            continue

        if returned_pid == process_id:
            return True

    return False


def load_state(
    path: Path,
) -> dict[str, Any]:
    return json.loads(
        path.read_text(
            encoding="utf-8-sig",
        )
    )


def service_map(
    state: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    services = state.get(
        "services"
    )

    if not isinstance(
        services,
        list,
    ):
        return {}

    return {
        str(
            service.get(
                "name"
            )
        ): service
        for service in services
        if isinstance(
            service,
            dict,
        )
    }


def process_id_map(
    services: dict[str, dict[str, Any]],
) -> dict[str, int]:
    return {
        name: int(
            service[
                "process_id"
            ]
        )
        for name, service in services.items()
    }


def path_map(
    services: dict[str, dict[str, Any]],
    key: str,
) -> dict[str, str]:
    return {
        name: str(
            service.get(
                key
            )
        )
        for name, service in services.items()
    }


print("=" * 92)
print(
    "MILESTONE 11.1C-2 — CONTROLLED COLD-START, "
    "OWNERSHIP AND SHUTDOWN ACCEPTANCE"
)
print("=" * 92)

check(
    "Startup manager exists",
    START_PATH.exists(),
    str(
        START_PATH
    ),
)

check(
    "Stop manager exists",
    STOP_PATH.exists(),
    str(
        STOP_PATH
    ),
)

check(
    "No active manager state exists before cold start",
    not STATE_PATH.exists(),
    str(
        STATE_PATH
    ),
)

for service_name, contract in (
    SERVICE_CONTRACTS.items()
):
    port = int(
        contract[
            "port"
        ]
    )

    check(
        f"{service_name} port is closed before cold start",
        not tcp_open(
            port
        ),
        f"Port {port}",
    )


try:
    # ========================================================
    # Manager validation
    # ========================================================

    start_validation = run_manager(
        START_PATH,
        "-ValidateOnly",
    )

    check(
        "Startup-manager validation succeeds",
        (
            "startup manager validation: PASSED"
            in start_validation
        ),
        start_validation,
    )

    stop_validation = run_manager(
        STOP_PATH,
        "-ValidateOnly",
    )

    check(
        "Stop-manager validation succeeds",
        (
            "stop manager validation: PASSED"
            in stop_validation
        ),
        stop_validation,
    )

    # ========================================================
    # First manager-owned cold start
    # ========================================================

    print()
    print("=" * 92)
    print("FIRST MANAGER-OWNED COLD START")
    print("=" * 92)

    first_start_output = run_manager(
        START_PATH
    )

    manager_started = True

    check(
        "First startup reports all services healthy",
        (
            "AI Voice Studio local services: HEALTHY"
            in first_start_output
        ),
        first_start_output,
    )

    started_summary_count = sum(
        1
        for service_name in SERVICE_CONTRACTS
        if (
            f"{service_name} = started"
            in first_start_output
        )
    )

    check(
        "First startup reports four newly started services",
        started_summary_count == 4,
        (
            "Started summaries="
            f"{started_summary_count}"
        ),
    )

    check(
        "Active state exists after first startup",
        STATE_PATH.exists(),
        str(
            STATE_PATH
        ),
    )

    first_state = load_state(
        STATE_PATH
    )

    first_services = service_map(
        first_state
    )

    check(
        "First state contains four services",
        len(
            first_services
        )
        == 4,
        repr(
            first_services
        ),
    )

    check(
        "First state contains expected service names",
        set(
            first_services
        )
        == set(
            SERVICE_CONTRACTS
        ),
        repr(
            set(
                first_services
            )
        ),
    )

    check(
        "Every first-start status is started",
        all(
            service.get(
                "status"
            )
            == "started"
            for service in first_services.values()
        ),
        repr(
            first_services
        ),
    )

    check(
        "Every first-start service is manager-owned",
        all(
            service.get(
                "started_by_manager"
            )
            is True
            for service in first_services.values()
        ),
        repr(
            first_services
        ),
    )

    valid_process_ids = all(
        isinstance(
            service.get(
                "process_id"
            ),
            int,
        )
        and int(
            service[
                "process_id"
            ]
        )
        > 0
        for service in first_services.values()
    )

    check(
        "Every first-start service has a valid process ID",
        valid_process_ids,
        repr(
            first_services
        ),
    )

    first_process_ids = process_id_map(
        first_services
    )

    check(
        "Every first-start process is alive",
        all(
            process_alive(
                process_id
            )
            for process_id in first_process_ids.values()
        ),
        repr(
            first_process_ids
        ),
    )

    check(
        "Every first-start service has a stdout log path",
        all(
            isinstance(
                service.get(
                    "stdout_log"
                ),
                str,
            )
            and bool(
                service[
                    "stdout_log"
                ]
            )
            for service in first_services.values()
        ),
        repr(
            first_services
        ),
    )

    check(
        "Every first-start service has a stderr log path",
        all(
            isinstance(
                service.get(
                    "stderr_log"
                ),
                str,
            )
            and bool(
                service[
                    "stderr_log"
                ]
            )
            for service in first_services.values()
        ),
        repr(
            first_services
        ),
    )

    check(
        "Every first-start stdout log exists",
        all(
            Path(
                service[
                    "stdout_log"
                ]
            ).exists()
            for service in first_services.values()
        ),
        repr(
            path_map(
                first_services,
                "stdout_log",
            )
        ),
    )

    check(
        "Every first-start stderr log exists",
        all(
            Path(
                service[
                    "stderr_log"
                ]
            ).exists()
            for service in first_services.values()
        ),
        repr(
            path_map(
                first_services,
                "stderr_log",
            )
        ),
    )

    for service_name, contract in (
        SERVICE_CONTRACTS.items()
    ):
        port = int(
            contract[
                "port"
            ]
        )

        health_url = str(
            contract[
                "health_url"
            ]
        )

        check(
            f"{service_name} TCP is listening after first start",
            tcp_open(
                port
            ),
            f"Port {port}",
        )

        check(
            f"{service_name} HTTP is healthy after first start",
            http_healthy(
                health_url
            ),
            health_url,
        )

    REPORT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    SNAPSHOT_PATH.write_text(
        json.dumps(
            first_state,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    check(
        "First-start ownership snapshot was saved",
        (
            SNAPSHOT_PATH.exists()
            and SNAPSHOT_PATH.stat().st_size
            > 0
        ),
        str(
            SNAPSHOT_PATH
        ),
    )

    # ========================================================
    # Second start: preserve ownership and process IDs
    # ========================================================

    print()
    print("=" * 92)
    print("SECOND START — IDEMPOTENCY AND OWNERSHIP")
    print("=" * 92)

    second_start_output = run_manager(
        START_PATH
    )

    check(
        "Second startup still reports all services healthy",
        (
            "AI Voice Studio local services: HEALTHY"
            in second_start_output
        ),
        second_start_output,
    )

    check(
        "Second startup preserves ownership for four services",
        second_start_output.count(
            "MANAGER OWNERSHIP PRESERVED"
        )
        == 4,
        second_start_output,
    )

    check(
        "Active state exists after second startup",
        STATE_PATH.exists(),
        str(
            STATE_PATH
        ),
    )

    second_state = load_state(
        STATE_PATH
    )

    second_services = service_map(
        second_state
    )

    check(
        "Second state contains four services",
        len(
            second_services
        )
        == 4,
        repr(
            second_services
        ),
    )

    check(
        "Second state contains expected service names",
        set(
            second_services
        )
        == set(
            SERVICE_CONTRACTS
        ),
        repr(
            set(
                second_services
            )
        ),
    )

    check(
        "Every second-start status is already_running",
        all(
            service.get(
                "status"
            )
            == "already_running"
            for service in second_services.values()
        ),
        repr(
            second_services
        ),
    )

    check(
        "Every second-start service remains manager-owned",
        all(
            service.get(
                "started_by_manager"
            )
            is True
            for service in second_services.values()
        ),
        repr(
            second_services
        ),
    )

    second_process_ids = process_id_map(
        second_services
    )

    check(
        "Second startup preserves every process ID",
        second_process_ids
        == first_process_ids,
        (
            f"First={first_process_ids}; "
            f"Second={second_process_ids}"
        ),
    )

    check(
        "Second startup preserves stdout log ownership",
        path_map(
            second_services,
            "stdout_log",
        )
        == path_map(
            first_services,
            "stdout_log",
        ),
    )

    check(
        "Second startup preserves stderr log ownership",
        path_map(
            second_services,
            "stderr_log",
        )
        == path_map(
            first_services,
            "stderr_log",
        ),
    )

    check(
        "Every preserved manager process remains alive",
        all(
            process_alive(
                process_id
            )
            for process_id in second_process_ids.values()
        ),
        repr(
            second_process_ids
        ),
    )

    for service_name, contract in (
        SERVICE_CONTRACTS.items()
    ):
        port = int(
            contract[
                "port"
            ]
        )

        health_url = str(
            contract[
                "health_url"
            ]
        )

        check(
            f"{service_name} TCP remains listening after second start",
            tcp_open(
                port
            ),
            f"Port {port}",
        )

        check(
            f"{service_name} HTTP remains healthy after second start",
            http_healthy(
                health_url
            ),
            health_url,
        )

    # ========================================================
    # Manager-owned shutdown
    # ========================================================

    print()
    print("=" * 92)
    print("MANAGER-OWNED SHUTDOWN")
    print("=" * 92)

    stop_output = run_manager(
        STOP_PATH
    )

    check(
        "Stop manager reports four stopped process trees",
        (
            "Managed process trees stopped: 4"
            in stop_output
        ),
        stop_output,
    )

    shutdown_completed = True

    all_ports_closed = wait_until(
        lambda: all(
            not tcp_open(
                int(
                    contract[
                        "port"
                    ]
                )
            )
            for contract in SERVICE_CONTRACTS.values()
        ),
        timeout_seconds=90,
        interval_seconds=1,
    )

    check(
        "Active manager state is removed after shutdown",
        not STATE_PATH.exists(),
        str(
            STATE_PATH
        ),
    )

    check(
        "Last manager state is retained after shutdown",
        LAST_STATE_PATH.exists(),
        str(
            LAST_STATE_PATH
        ),
    )

    last_state = load_state(
        LAST_STATE_PATH
    )

    last_services = service_map(
        last_state
    )

    check(
        "Last state contains four services",
        len(
            last_services
        )
        == 4,
        repr(
            last_services
        ),
    )

    check(
        "Last state contains expected service names",
        set(
            last_services
        )
        == set(
            SERVICE_CONTRACTS
        ),
        repr(
            set(
                last_services
            )
        ),
    )

    check(
        "Last state records all services as manager-owned",
        all(
            service.get(
                "started_by_manager"
            )
            is True
            for service in last_services.values()
        ),
        repr(
            last_services
        ),
    )

    check(
        "Last state retains the original process IDs",
        process_id_map(
            last_services
        )
        == first_process_ids,
        (
            f"Expected={first_process_ids}; "
            f"Actual={process_id_map(last_services)}"
        ),
    )

    for service_name, contract in (
        SERVICE_CONTRACTS.items()
    ):
        port = int(
            contract[
                "port"
            ]
        )

        check(
            f"{service_name} port is closed after shutdown",
            (
                all_ports_closed
                and not tcp_open(
                    port
                )
            ),
            f"Port {port}",
        )

    report = {
        "milestone": "11.1C-2",
        "created_at": (
            datetime.now().isoformat()
        ),
        "first_state": first_state,
        "second_state": second_state,
        "last_state": last_state,
        "process_ids_preserved": (
            second_process_ids
            == first_process_ids
        ),
        "ownership_preserved": all(
            service.get(
                "started_by_manager"
            )
            is True
            for service in second_services.values()
        ),
        "shutdown_completed": (
            all_ports_closed
            and not STATE_PATH.exists()
        ),
        "snapshot_path": str(
            SNAPSHOT_PATH
        ),
    }

    REPORT_PATH.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )

    check(
        "Cold-start and shutdown report was saved",
        (
            REPORT_PATH.exists()
            and REPORT_PATH.stat().st_size
            > 0
        ),
        str(
            REPORT_PATH
        ),
    )

    print()
    print("=" * 92)
    print(
        "MILESTONE 11.1C-2 CONTROLLED COLD-START "
        "AND SHUTDOWN: PASSED"
    )
    print("=" * 92)

    print(
        "Checks passed:",
        checks_passed,
    )

    print()
    print(
        "Report:",
        REPORT_PATH,
    )

    print(
        "Final service state: STOPPED"
    )

finally:
    if (
        manager_started
        and not shutdown_completed
        and STATE_PATH.exists()
    ):
        print()
        print(
            "Running emergency manager cleanup..."
        )

        try:
            run_manager(
                STOP_PATH
            )

        except Exception as cleanup_error:
            print(
                "Emergency cleanup failed:",
                cleanup_error,
            )
