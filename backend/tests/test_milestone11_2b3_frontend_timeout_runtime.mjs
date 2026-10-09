import {
  existsSync,
  mkdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";

import {
  dirname,
  join,
} from "node:path";

import {
  pathToFileURL,
} from "node:url";


const projectRoot =
  process.env.AI_VOICE_STUDIO_PROJECT_ROOT;

const reportPath =
  process.env.MILESTONE11_2B3_REPORT_PATH;


if (!projectRoot) {
  throw new Error(
    "AI_VOICE_STUDIO_PROJECT_ROOT is missing.",
  );
}

if (!reportPath) {
  throw new Error(
    "MILESTONE11_2B3_REPORT_PATH is missing.",
  );
}


const backendRoot =
  join(
    projectRoot,
    "backend",
  );

const apiPath =
  join(
    projectRoot,
    "frontend",
    "src",
    "api.js",
  );

const temporaryRoot =
  join(
    backendRoot,
    "tests",
    ".milestone11_2b3_runtime",
  );

const temporaryModulePath =
  join(
    temporaryRoot,
    "api_runtime_test.mjs",
  );


let checksPassed = 0;


function check(
  name,
  condition,
  detail = "",
) {
  if (!condition) {
    let message =
      `${name}: FAILED`;

    if (detail) {
      message +=
        `\n${detail}`;
    }

    throw new Error(
      message,
    );
  }

  checksPassed += 1;

  console.log(
    `${name}: PASSED`,
  );
}


function createJsonResponse(
  payload = {
    ok: true,
  },
  status = 200,
) {
  return new Response(
    JSON.stringify(payload),
    {
      status,
      headers: {
        "content-type":
          "application/json",
      },
    },
  );
}


function abortError() {
  return new DOMException(
    "The operation was aborted.",
    "AbortError",
  );
}


function createPendingAbortAwareFetch(
  onAbort = () => {},
) {
  return (
    _url,
    options = {},
  ) =>
    new Promise(
      (_resolve, reject) => {
        const rejectForAbort = () => {
          onAbort(
            options.signal,
          );

          reject(
            abortError(),
          );
        };

        if (options.signal?.aborted) {
          rejectForAbort();
          return;
        }

        options.signal?.addEventListener(
          "abort",
          rejectForAbort,
          {
            once: true,
          },
        );
      },
    );
}


async function captureRequestTimer(
  operation,
) {
  const nativeSetTimeout =
    globalThis.setTimeout;

  const nativeClearTimeout =
    globalThis.clearTimeout;

  const previousFetch =
    globalThis.fetch;

  const delays = [];
  let clearCount = 0;

  globalThis.setTimeout = (
    callback,
    delay,
    ...argumentsList
  ) => {
    delays.push(
      Number(delay),
    );

    return nativeSetTimeout(
      callback,
      delay,
      ...argumentsList,
    );
  };

  globalThis.clearTimeout = (
    timerId,
  ) => {
    clearCount += 1;

    return nativeClearTimeout(
      timerId,
    );
  };

  globalThis.fetch = async () =>
    createJsonResponse();

  try {
    await operation();
  } finally {
    globalThis.setTimeout =
      nativeSetTimeout;

    globalThis.clearTimeout =
      nativeClearTimeout;

    globalThis.fetch =
      previousFetch;
  }

  return {
    delays,
    clearCount,
  };
}


console.log(
  "=".repeat(92),
);

console.log(
  "MILESTONE 11.2B-3 — FRONTEND REQUEST TIMEOUT RUNTIME ACCEPTANCE",
);

console.log(
  "=".repeat(92),
);


check(
  "Frontend API source exists",
  existsSync(
    apiPath,
  ),
  apiPath,
);

check(
  "Node provides AbortController",
  typeof AbortController === "function",
);

check(
  "Node provides DOMException",
  typeof DOMException === "function",
);

check(
  "Node provides Fetch response APIs",
  (
    typeof Response === "function" &&
    typeof Headers === "function" &&
    typeof FormData === "function"
  ),
);


const source =
  readFileSync(
    apiPath,
    "utf8",
  );

const transformedSource =
  source.replaceAll(
    "import.meta.env",
    "({})",
  ) +
  `

export {
  request,
  DEFAULT_REQUEST_TIMEOUT_MS,
  VOICE_UPLOAD_TIMEOUT_MS,
  SPEECH_GENERATION_TIMEOUT_MS,
};
`;


rmSync(
  temporaryRoot,
  {
    recursive: true,
    force: true,
  },
);

mkdirSync(
  temporaryRoot,
  {
    recursive: true,
  },
);

writeFileSync(
  temporaryModulePath,
  transformedSource,
  "utf8",
);


const originalFetch =
  globalThis.fetch;

const nativeSetTimeout =
  globalThis.setTimeout;

const nativeClearTimeout =
  globalThis.clearTimeout;


try {
  const moduleUrl =
    pathToFileURL(
      temporaryModulePath,
    );

  moduleUrl.searchParams.set(
    "runtime",
    Date.now().toString(),
  );

  const apiModule =
    await import(
      moduleUrl.href
    );

  const {
    api,
    request,
    DEFAULT_REQUEST_TIMEOUT_MS,
    VOICE_UPLOAD_TIMEOUT_MS,
    SPEECH_GENERATION_TIMEOUT_MS,
  } = apiModule;


  check(
    "Shared request helper is available at runtime",
    typeof request === "function",
  );

  check(
    "API method registry is available at runtime",
    (
      api &&
      typeof api.generateSpeech === "function" &&
      typeof api.uploadVoice === "function"
    ),
  );

  check(
    "Default timeout equals 120000 milliseconds",
    DEFAULT_REQUEST_TIMEOUT_MS === 120000,
  );

  check(
    "Voice-upload timeout equals 600000 milliseconds",
    VOICE_UPLOAD_TIMEOUT_MS === 600000,
  );

  check(
    "Speech-generation timeout equals 1800000 milliseconds",
    SPEECH_GENERATION_TIMEOUT_MS === 1800000,
  );


  let successfulFetchOptions = null;
  const successTimerDelays = [];
  let successTimerClearCount = 0;

  globalThis.setTimeout = (
    callback,
    delay,
    ...argumentsList
  ) => {
    successTimerDelays.push(
      Number(delay),
    );

    return nativeSetTimeout(
      callback,
      delay,
      ...argumentsList,
    );
  };

  globalThis.clearTimeout = (
    timerId,
  ) => {
    successTimerClearCount += 1;

    return nativeClearTimeout(
      timerId,
    );
  };

  globalThis.fetch = async (
    _url,
    options,
  ) => {
    successfulFetchOptions =
      options;

    return createJsonResponse(
      {
        runtime:
          "success",
      },
    );
  };

  const successResult =
    await request(
      "/runtime-success",
      {
        method: "POST",
        body: JSON.stringify(
          {
            test: true,
          },
        ),
        timeoutMs: 500,
      },
    );

  globalThis.setTimeout =
    nativeSetTimeout;

  globalThis.clearTimeout =
    nativeClearTimeout;


  check(
    "Successful JSON response is returned",
    successResult.runtime === "success",
  );

  check(
    "Controlled AbortSignal is passed to fetch",
    successfulFetchOptions?.signal instanceof AbortSignal,
  );

  check(
    "Custom timeout option is removed before fetch",
    !(
      "timeoutMs"
      in successfulFetchOptions
    ),
  );

  check(
    "Successful request schedules its timeout",
    successTimerDelays.includes(
      500,
    ),
  );

  check(
    "Successful request clears its timeout",
    successTimerClearCount >= 1,
  );


  const defaultTimer =
    await captureRequestTimer(
      () =>
        api.getVoices(),
    );

  check(
    "Normal API request uses the two-minute timeout",
    defaultTimer.delays.includes(
      120000,
    ),
  );

  check(
    "Normal API request clears its timer",
    defaultTimer.clearCount >= 1,
  );


  const uploadBlob =
    new Blob(
      [
        "runtime-audio",
      ],
      {
        type: "audio/wav",
      },
    );

  const uploadTimer =
    await captureRequestTimer(
      () =>
        api.uploadVoice(
          {
            voiceName:
              "Runtime Test Voice",
            language:
              "English",
            file:
              uploadBlob,
          },
        ),
    );

  check(
    "Voice upload uses the ten-minute timeout",
    uploadTimer.delays.includes(
      600000,
    ),
  );


  const generationTimer =
    await captureRequestTimer(
      () =>
        api.generateSpeech(
          {
            voice_id: 10,
            text:
              "Runtime timeout test.",
            speed: 1,
            volume: 1,
            bass: 0,
            style: "neutral",
            engine: "auto",
            allow_fallback: true,
          },
        ),
    );

  check(
    "Speech generation uses the thirty-minute timeout",
    generationTimer.delays.includes(
      1800000,
    ),
  );


  let timeoutSignalAborted = false;

  globalThis.fetch =
    createPendingAbortAwareFetch(
      (signal) => {
        timeoutSignalAborted =
          Boolean(
            signal?.aborted,
          );
      },
    );

  const timeoutStartedAt =
    performance.now();

  let timeoutErrorMessage = "";

  try {
    await request(
      "/runtime-timeout",
      {
        timeoutMs: 40,
      },
    );
  } catch (error) {
    timeoutErrorMessage =
      error.message;
  }

  const timeoutElapsed =
    performance.now() -
    timeoutStartedAt;


  check(
    "Timeout aborts the controlled fetch signal",
    timeoutSignalAborted,
  );

  check(
    "Timeout receives a distinct readable error",
    timeoutErrorMessage
      .toLowerCase()
      .includes(
        "timed out",
      ),
    timeoutErrorMessage,
  );

  check(
    "Timeout completes without hanging",
    timeoutElapsed < 1500,
    `${timeoutElapsed.toFixed(1)} ms`,
  );


  const externalController =
    new AbortController();

  let externalAbortReachedFetch =
    false;

  globalThis.fetch =
    createPendingAbortAwareFetch(
      (signal) => {
        externalAbortReachedFetch =
          Boolean(
            signal?.aborted,
          );
      },
    );

  nativeSetTimeout(
    () => {
      externalController.abort(
        "runtime-manual-cancellation",
      );
    },
    30,
  );

  const cancellationStartedAt =
    performance.now();

  let cancellationErrorMessage = "";

  try {
    await request(
      "/runtime-cancellation",
      {
        timeoutMs: 1000,
        signal:
          externalController.signal,
      },
    );
  } catch (error) {
    cancellationErrorMessage =
      error.message;
  }

  const cancellationElapsed =
    performance.now() -
    cancellationStartedAt;


  check(
    "External cancellation reaches the controlled fetch signal",
    externalAbortReachedFetch,
  );

  check(
    "External cancellation receives a distinct error",
    cancellationErrorMessage ===
      "The request was cancelled.",
    cancellationErrorMessage,
  );

  check(
    "External cancellation occurs before request timeout",
    cancellationElapsed < 900,
    `${cancellationElapsed.toFixed(1)} ms`,
  );


  const trackedExternalSignal = {
    aborted: false,
    reason: undefined,
    listener: null,
    addCount: 0,
    removeCount: 0,

    addEventListener(
      eventName,
      listener,
    ) {
      if (eventName === "abort") {
        this.listener =
          listener;

        this.addCount += 1;
      }
    },

    removeEventListener(
      eventName,
      listener,
    ) {
      if (
        eventName === "abort" &&
        listener === this.listener
      ) {
        this.removeCount += 1;
      }
    },
  };

  globalThis.fetch =
    async () =>
      createJsonResponse(
        {
          listener:
            "cleaned",
        },
      );

  await request(
    "/runtime-listener-cleanup",
    {
      timeoutMs: 500,
      signal:
        trackedExternalSignal,
    },
  );


  check(
    "External abort listener is registered",
    trackedExternalSignal.addCount === 1,
  );

  check(
    "External abort listener is removed after completion",
    trackedExternalSignal.removeCount === 1,
  );


  globalThis.fetch =
    async () =>
      createJsonResponse(
        {
          detail:
            "IndicF5 runtime unavailable",
        },
        503,
      );

  let httpErrorMessage = "";

  try {
    await request(
      "/runtime-http-error",
      {
        timeoutMs: 500,
      },
    );
  } catch (error) {
    httpErrorMessage =
      error.message;
  }


  check(
    "Backend HTTP error detail remains readable",
    httpErrorMessage.includes(
      "IndicF5 runtime unavailable",
    ),
    httpErrorMessage,
  );


  globalThis.fetch =
    async () =>
      new Response(
        null,
        {
          status: 204,
        },
      );

  const emptyResult =
    await request(
      "/runtime-empty-response",
      {
        timeoutMs: 500,
      },
    );


  check(
    "HTTP 204 response still returns null",
    emptyResult === null,
  );


  const runtimeFormData =
    new FormData();

  runtimeFormData.append(
    "voice_name",
    "Runtime Voice",
  );

  let formDataContentTypePresent =
    true;

  globalThis.fetch =
    async (
      _url,
      options,
    ) => {
      const headers =
        new Headers(
          options.headers,
        );

      formDataContentTypePresent =
        headers.has(
          "Content-Type",
        );

      return createJsonResponse();
    };

  await request(
    "/runtime-form-data",
    {
      method: "POST",
      body:
        runtimeFormData,
      timeoutMs: 500,
    },
  );


  check(
    "FormData still leaves multipart Content-Type to the browser",
    !formDataContentTypePresent,
  );


  globalThis.fetch =
    async () => {
      throw new TypeError(
        "Simulated connection refusal",
      );
    };

  let connectionErrorMessage = "";

  try {
    await request(
      "/runtime-connection-error",
      {
        timeoutMs: 500,
      },
    );
  } catch (error) {
    connectionErrorMessage =
      error.message;
  }


  check(
    "Backend connection error mapping remains available",
    connectionErrorMessage.includes(
      "Could not connect to the backend.",
    ),
    connectionErrorMessage,
  );
} finally {
  globalThis.fetch =
    originalFetch;

  globalThis.setTimeout =
    nativeSetTimeout;

  globalThis.clearTimeout =
    nativeClearTimeout;

  rmSync(
    temporaryRoot,
    {
      recursive: true,
      force: true,
    },
  );
}


check(
  "Temporary runtime module was removed",
  !existsSync(
    temporaryRoot,
  ),
);


const report = {
  milestone:
    "11.2B-3",
  created_at:
    new Date().toISOString(),
  mode:
    "runtime acceptance with mocked fetch",
  application_files_modified:
    false,
  services_started:
    false,
  checks_passed:
    checksPassed + 1,
  timeouts_ms: {
    default:
      120000,
    voice_upload:
      600000,
    speech_generation:
      1800000,
  },
  verified_behaviour: {
    successful_json_response:
      true,
    controlled_abort_signal:
      true,
    timeout_option_removed_before_fetch:
      true,
    timeout_aborts_fetch:
      true,
    timeout_error_mapping:
      true,
    external_cancellation:
      true,
    timer_cleanup:
      true,
    external_listener_cleanup:
      true,
    backend_http_error_mapping:
      true,
    backend_connection_error_mapping:
      true,
    form_data_header_preservation:
      true,
    http_204_handling:
      true,
  },
};


mkdirSync(
  dirname(
    reportPath,
  ),
  {
    recursive: true,
  },
);

writeFileSync(
  reportPath,
  JSON.stringify(
    report,
    null,
    2,
  ) + "\n",
  "utf8",
);


check(
  "Runtime acceptance report was saved",
  (
    existsSync(
      reportPath,
    ) &&
    readFileSync(
      reportPath,
      "utf8",
    ).length > 0
  ),
  reportPath,
);


console.log();

console.log(
  "=".repeat(92),
);

console.log(
  "MILESTONE 11.2B-3 FRONTEND REQUEST TIMEOUT RUNTIME ACCEPTANCE: PASSED",
);

console.log(
  "=".repeat(92),
);

console.log(
  `Checks passed: ${checksPassed}`,
);

console.log(
  "Application files modified: NO",
);

console.log(
  "Services started: NO",
);

console.log();

console.log(
  `Report: ${reportPath}`,
);
