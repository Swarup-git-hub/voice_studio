from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent

API_PATH = (
    PROJECT_ROOT
    / "frontend"
    / "src"
    / "api.js"
)

REPORT_PATH = Path(
    os.environ[
        "MILESTONE11_2B2_REPORT_PATH"
    ]
).resolve()


OLD_REQUEST = '''async function request(path, options = {}) {
  const headers = new Headers(
    options.headers || {},
  );

  const bodyIsFormData =
    typeof FormData !== "undefined" &&
    options.body instanceof FormData;

  /*
   * Do not manually set Content-Type for FormData.
   * The browser must add the multipart boundary.
   */
  if (
    options.body &&
    !bodyIsFormData &&
    !headers.has("Content-Type")
  ) {
    headers.set(
      "Content-Type",
      "application/json",
    );
  }

  let response;

  try {
    response = await fetch(
      buildApiUrl(path),
      {
        ...options,
        headers,
      },
    );
  } catch (error) {
    throw new Error(
      "Could not connect to the backend. " +
      "Confirm FastAPI is running on port 8000 " +
      "and the Vite proxy is configured.",
    );
  }

  if (!response.ok) {
    const message =
      await getErrorMessage(response);

    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  const contentType =
    response.headers.get("content-type") || "";

  if (
    contentType.includes("application/json")
  ) {
    return response.json();
  }

  return response;
}'''


NEW_REQUEST = '''const DEFAULT_REQUEST_TIMEOUT_MS =
  2 * 60 * 1000;

const VOICE_UPLOAD_TIMEOUT_MS =
  10 * 60 * 1000;

const SPEECH_GENERATION_TIMEOUT_MS =
  30 * 60 * 1000;


function formatTimeoutDuration(timeoutMs) {
  const wholeMinutes =
    timeoutMs / (60 * 1000);

  if (Number.isInteger(wholeMinutes)) {
    return (
      `${wholeMinutes} minute` +
      `${wholeMinutes === 1 ? "" : "s"}`
    );
  }

  const wholeSeconds =
    Math.ceil(timeoutMs / 1000);

  return (
    `${wholeSeconds} second` +
    `${wholeSeconds === 1 ? "" : "s"}`
  );
}


function getTimeoutError(timeoutMs) {
  return new Error(
    "The request timed out after " +
    `${formatTimeoutDuration(timeoutMs)}. ` +
    "The backend may still be processing. " +
    "Check the service status before trying again.",
  );
}


async function request(path, options = {}) {
  const {
    timeoutMs = DEFAULT_REQUEST_TIMEOUT_MS,
    signal: externalSignal,
    ...fetchOptions
  } = options;

  if (
    !Number.isFinite(timeoutMs) ||
    timeoutMs <= 0
  ) {
    throw new Error(
      "Request timeout must be a positive number.",
    );
  }

  const headers = new Headers(
    fetchOptions.headers || {},
  );

  const bodyIsFormData =
    typeof FormData !== "undefined" &&
    fetchOptions.body instanceof FormData;

  /*
   * Do not manually set Content-Type for FormData.
   * The browser must add the multipart boundary.
   */
  if (
    fetchOptions.body &&
    !bodyIsFormData &&
    !headers.has("Content-Type")
  ) {
    headers.set(
      "Content-Type",
      "application/json",
    );
  }

  const controller =
    new AbortController();

  let timeoutTriggered = false;
  let externalAbortHandler = null;

  if (externalSignal) {
    if (externalSignal.aborted) {
      controller.abort(
        externalSignal.reason,
      );
    } else {
      externalAbortHandler = () => {
        controller.abort(
          externalSignal.reason,
        );
      };

      externalSignal.addEventListener(
        "abort",
        externalAbortHandler,
        {
          once: true,
        },
      );
    }
  }

  const timeoutId = setTimeout(
    () => {
      timeoutTriggered = true;
      controller.abort();
    },
    timeoutMs,
  );

  let response;

  try {
    response = await fetch(
      buildApiUrl(path),
      {
        ...fetchOptions,
        headers,
        signal: controller.signal,
      },
    );
  } catch (error) {
    if (timeoutTriggered) {
      throw getTimeoutError(
        timeoutMs,
      );
    }

    if (
      externalSignal?.aborted ||
      error?.name === "AbortError"
    ) {
      throw new Error(
        "The request was cancelled.",
      );
    }

    throw new Error(
      "Could not connect to the backend. " +
      "Confirm FastAPI is running on port 8000 " +
      "and the Vite proxy is configured.",
    );
  } finally {
    clearTimeout(
      timeoutId,
    );

    if (
      externalSignal &&
      externalAbortHandler
    ) {
      externalSignal.removeEventListener(
        "abort",
        externalAbortHandler,
      );
    }
  }

  if (!response.ok) {
    const message =
      await getErrorMessage(response);

    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  const contentType =
    response.headers.get("content-type") || "";

  if (
    contentType.includes("application/json")
  ) {
    return response.json();
  }

  return response;
}'''


source = API_PATH.read_text(
    encoding="utf-8-sig"
)

if (
    "const DEFAULT_REQUEST_TIMEOUT_MS"
    in source
    or "new AbortController()"
    in source
):
    raise RuntimeError(
        "A request-timeout implementation already exists. "
        "No files were modified."
    )


old_request_count = source.count(
    OLD_REQUEST
)

if old_request_count != 1:
    raise RuntimeError(
        "Expected exactly one original request helper, "
        f"found {old_request_count}. "
        "No files were modified."
    )


updated_source = source.replace(
    OLD_REQUEST,
    NEW_REQUEST,
    1,
)


form_data_pattern = re.compile(
    r"^(?P<indent>\s*)body:\s*formData,\s*$",
    flags=re.MULTILINE,
)


def add_upload_timeout(
    match: re.Match[str],
) -> str:
    indent = match.group(
        "indent"
    )

    return (
        f"{indent}body: formData,\n"
        f"{indent}timeoutMs: VOICE_UPLOAD_TIMEOUT_MS,"
    )


updated_source, upload_replacement_count = (
    form_data_pattern.subn(
        add_upload_timeout,
        updated_source,
        count=1,
    )
)

if upload_replacement_count != 1:
    raise RuntimeError(
        "Expected exactly one FormData upload request, "
        f"patched {upload_replacement_count}. "
        "No files were modified."
    )


generate_start_marker = (
    "  generateSpeech(payload) {"
)

generate_start = updated_source.find(
    generate_start_marker
)

if generate_start < 0:
    raise RuntimeError(
        "generateSpeech method was not found. "
        "No files were modified."
    )


generate_end = updated_source.find(
    "\n  },",
    generate_start,
)

if generate_end < 0:
    raise RuntimeError(
        "Could not locate the end of generateSpeech. "
        "No files were modified."
    )

generate_end += len(
    "\n  },"
)

generate_segment = updated_source[
    generate_start:generate_end
]

required_generate_markers = [
    '"/speech/generate"',
    'method: "POST"',
    "body: JSON.stringify(payload),",
]

for marker in required_generate_markers:
    if marker not in generate_segment:
        raise RuntimeError(
            "generateSpeech is missing expected marker: "
            f"{marker}. No files were modified."
        )


generation_body_marker = (
    "        body: JSON.stringify(payload),\n"
)

if generate_segment.count(
    generation_body_marker
) != 1:
    raise RuntimeError(
        "The generation request body marker was not unique. "
        "No files were modified."
    )


updated_generate_segment = (
    generate_segment.replace(
        generation_body_marker,
        (
            generation_body_marker
            + "        timeoutMs: "
            + "SPEECH_GENERATION_TIMEOUT_MS,\n"
        ),
        1,
    )
)

updated_source = (
    updated_source[:generate_start]
    + updated_generate_segment
    + updated_source[generate_end:]
)


required_final_markers = [
    "const DEFAULT_REQUEST_TIMEOUT_MS",
    "const VOICE_UPLOAD_TIMEOUT_MS",
    "const SPEECH_GENERATION_TIMEOUT_MS",
    "new AbortController()",
    "setTimeout(",
    "clearTimeout(",
    "signal: controller.signal",
    'error?.name === "AbortError"',
    '"The request was cancelled."',
    "throw getTimeoutError(",
    "timeoutMs: VOICE_UPLOAD_TIMEOUT_MS",
    "timeoutMs: SPEECH_GENERATION_TIMEOUT_MS",
    "...fetchOptions",
    "fetchOptions.body instanceof FormData",
]

for marker in required_final_markers:
    if marker not in updated_source:
        raise RuntimeError(
            "Updated API client is missing marker: "
            f"{marker}. No files were modified."
        )


if "        ...options,\n" in updated_source:
    raise RuntimeError(
        "The custom timeoutMs option would still be passed "
        "to fetch(). No files were modified."
    )


API_PATH.write_text(
    updated_source,
    encoding="utf-8",
)


report = {
    "milestone": "11.2B-2",
    "created_at": datetime.now().isoformat(),
    "application_file_modified": str(
        API_PATH
    ),
    "timeouts_ms": {
        "default": 120000,
        "voice_upload": 600000,
        "speech_generation": 1800000,
    },
    "features": {
        "abort_controller": True,
        "external_abort_signal": True,
        "timeout_error_mapping": True,
        "cancellation_error_mapping": True,
        "connection_error_mapping_preserved": True,
        "timer_cleanup": True,
        "external_listener_cleanup": True,
        "form_data_handling_preserved": True,
        "response_handling_preserved": True,
    },
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

print(
    "Default request timeout      : 120000 ms"
)

print(
    "Voice-upload timeout         : 600000 ms"
)

print(
    "Speech-generation timeout    : 1800000 ms"
)

print(
    "AbortController integration  : APPLIED"
)

print(
    "External signal integration  : APPLIED"
)

print(
    "Timer and listener cleanup   : APPLIED"
)

print(
    "Milestone 11.2B-2 frontend request "
    "timeout implementation: APPLIED"
)

print(
    "Implementation report:",
    REPORT_PATH,
)
