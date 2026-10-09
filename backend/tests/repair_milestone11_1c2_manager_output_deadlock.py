from __future__ import annotations

import ast
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]

TEST_PATH = (
    BACKEND_ROOT
    / "tests"
    / "test_milestone11_1c2_cold_start_shutdown.py"
)


def find_function(
    tree: ast.Module,
    expected_name: str,
) -> ast.FunctionDef:
    for node in tree.body:
        if (
            isinstance(
                node,
                ast.FunctionDef,
            )
            and node.name == expected_name
        ):
            return node

    raise RuntimeError(
        f"Function {expected_name} was not found."
    )


def source_offsets(
    source_bytes: bytes,
    node: ast.AST,
) -> tuple[int, int]:
    lines = source_bytes.splitlines(
        keepends=True
    )

    line_offsets: list[int] = []

    running_offset = 0

    for line in lines:
        line_offsets.append(
            running_offset
        )

        running_offset += len(
            line
        )

    start = (
        line_offsets[
            node.lineno - 1
        ]
        + node.col_offset
    )

    end = (
        line_offsets[
            node.end_lineno - 1
        ]
        + node.end_col_offset
    )

    return start, end


source = TEST_PATH.read_text(
    encoding="utf-8-sig"
)

tree = ast.parse(
    source,
    filename=str(
        TEST_PATH
    ),
)

run_manager_function = find_function(
    tree,
    "run_manager",
)

old_function_source = ast.get_source_segment(
    source,
    run_manager_function,
)

if old_function_source is None:
    raise RuntimeError(
        "Could not read the existing run_manager function."
    )

required_old_markers = [
    "subprocess.run(",
    "capture_output=True",
    "completed.stdout",
    "completed.stderr",
]

for marker in required_old_markers:
    if marker not in old_function_source:
        raise RuntimeError(
            "Existing run_manager function is missing "
            f"the expected marker: {marker}"
        )


replacement = '''def run_manager(
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
                    "Manager command exceeded its timeout.\\n"
                    f"Command: {command}\\n"
                    f"Timeout: {timeout_seconds} seconds\\n"
                    f"taskkill stdout:\\n{termination.stdout}\\n"
                    f"taskkill stderr:\\n{termination.stderr}\\n"
                    f"Manager stdout:\\n{stdout_text}\\n"
                    f"Manager stderr:\\n{stderr_text}"
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

    combined_output = "\\n".join(
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
            "Manager command failed.\\n"
            f"Command: {command}\\n"
            f"Exit code: {return_code}\\n"
            f"Standard output log: {stdout_path}\\n"
            f"Standard error log: {stderr_path}\\n"
            f"Output:\\n{combined_output}"
        )

    return combined_output
'''


source_bytes = source.encode(
    "utf-8"
)

start, end = source_offsets(
    source_bytes,
    run_manager_function,
)

updated_bytes = (
    source_bytes[:start]
    + replacement.encode(
        "utf-8"
    )
    + source_bytes[end:]
)

updated_source = updated_bytes.decode(
    "utf-8"
)

updated_tree = ast.parse(
    updated_source,
    filename=str(
        TEST_PATH
    ),
)

updated_function = find_function(
    updated_tree,
    "run_manager",
)

updated_function_source = ast.get_source_segment(
    updated_source,
    updated_function,
)

if updated_function_source is None:
    raise RuntimeError(
        "Could not inspect the repaired run_manager function."
    )

required_updated_markers = [
    "subprocess.Popen(",
    "manager_command_logs",
    "timeout_seconds = 1200",
    "Manager still running after",
    "taskkill.exe",
    "stdout_path.read_text",
    "stderr_path.read_text",
]

for marker in required_updated_markers:
    if marker not in updated_function_source:
        raise RuntimeError(
            "Repaired run_manager function is missing: "
            f"{marker}"
        )

for forbidden_marker in [
    "capture_output=True",
    "completed.stdout",
    "completed.stderr",
]:
    if forbidden_marker in updated_function_source:
        raise RuntimeError(
            "Old captured-pipe marker remains: "
            f"{forbidden_marker}"
        )

TEST_PATH.write_text(
    updated_source,
    encoding="utf-8",
)

print(
    "Milestone 11.1C-2 manager output-pipe "
    "deadlock repair: APPLIED"
)
