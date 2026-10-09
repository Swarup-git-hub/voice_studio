const API_PREFIX = "/api";


function buildApiUrl(path) {
  if (!path) {
    return "";
  }

  if (
    path.startsWith("http://") ||
    path.startsWith("https://")
  ) {
    return path;
  }

  const normalizedPath = path.startsWith("/")
    ? path
    : `/${path}`;

  return `${API_PREFIX}${normalizedPath}`;
}


async function getErrorMessage(response) {
  const fallbackMessage =
    `Request failed with status ${response.status}.`;

  try {
    const rawResponse = await response.text();

    if (!rawResponse) {
      return fallbackMessage;
    }

    try {
      const errorBody = JSON.parse(rawResponse);

      if (typeof errorBody.detail === "string") {
        return errorBody.detail;
      }

      if (Array.isArray(errorBody.detail)) {
        return errorBody.detail
          .map((item) => {
            const location = Array.isArray(item.loc)
              ? item.loc.join(" → ")
              : "";

            const message =
              item.msg || "Validation error";

            return location
              ? `${location}: ${message}`
              : message;
          })
          .join("; ");
      }

      if (errorBody.detail) {
        return JSON.stringify(errorBody.detail);
      }

      if (errorBody.message) {
        return errorBody.message;
      }

      return rawResponse;
    } catch {
      return rawResponse;
    }
  } catch {
    return fallbackMessage;
  }
}


const DEFAULT_REQUEST_TIMEOUT_MS =
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
}


export const api = {
  // =========================================================
  // Voice Library
  // =========================================================

  getVoices() {
    return request("/voice/list");
  },


  getVoice(voiceId) {
    return request(
      `/voice/${voiceId}`,
    );
  },


  uploadVoice({
    voiceName,
    language,
    file,
  }) {
    if (!file) {
      throw new Error(
        "A reference audio file is required.",
      );
    }

    const formData = new FormData();

    formData.append(
      "voice_name",
      voiceName,
    );

    formData.append(
      "language",
      language || "Mixed",
    );

    formData.append(
      "file",
      file,
    );

    return request(
      "/voice/upload",
      {
        method: "POST",
        body: formData,
        timeoutMs: VOICE_UPLOAD_TIMEOUT_MS,
      },
    );
  },


  updateVoice(
    voiceId,
    payload,
  ) {
    return request(
      `/voice/${voiceId}`,
      {
        method: "PUT",
        body: JSON.stringify(payload),
      },
    );
  },


  deleteVoice(voiceId) {
    return request(
      `/voice/${voiceId}`,
      {
        method: "DELETE",
      },
    );
  },


  referenceAudioUrl(voiceId) {
    return buildApiUrl(
      `/voice/${voiceId}/audio`,
    );
  },


  // =========================================================
  // Speech Generation
  // =========================================================

  generateSpeech(payload) {
    return request(
      "/speech/generate",
      {
        method: "POST",
        body: JSON.stringify(payload),
        timeoutMs: SPEECH_GENERATION_TIMEOUT_MS,
      },
    );
  },


  // =========================================================
  // Generated Audio History
  // =========================================================

  getHistory(limit = 50, offset = 0) {
    return request(
      `/speech/history?offset=${offset}&limit=${limit}`,
    );
  },


  getGeneration(generationId) {
    return request(
      `/speech/history/${generationId}`,
    );
  },


  deleteGeneration(generationId) {
    return request(
      `/speech/history/${generationId}`,
      {
        method: "DELETE",
      },
    );
  },


  audioUrl(item) {
    if (!item?.audio_url) {
      return "";
    }

    return buildApiUrl(
      item.audio_url,
    );
  },


  downloadUrl(item) {
    if (!item?.download_url) {
      return "";
    }

    return buildApiUrl(
      item.download_url,
    );
  },


  toApiUrl(path) {
    return buildApiUrl(path);
  },
};