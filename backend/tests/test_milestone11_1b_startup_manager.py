from __future__ import annotations

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
