import { useEffect, useMemo, useState } from "react";

import { api } from "./api";
import VoiceLibrary from "./VoiceLibrary";
import "./App.css";

const DEFAULT_TEXT =
  "Hello everyone! Welcome to AI Voice Studio. " +
  "Select a saved voice, enter your script, and generate narration for your content.";

const ENGINE_LABELS = {
  auto: "Automatic",
  cosyvoice: "CosyVoice",
  indicf5: "IndicF5",
  legacy: "Legacy",
};

const STYLE_LABELS = {
  neutral: "Neutral",
  professional: "Professional",
  energetic: "Energetic",
  calm: "Calm",
  storytelling: "Storytelling",
};

function formatEngine(engineValue) {
  return ENGINE_LABELS[engineValue] || engineValue || "Unknown";
}

function formatStyle(styleValue) {
  return STYLE_LABELS[styleValue] || STYLE_LABELS.neutral;
}

function formatDate(dateValue) {
  if (!dateValue) {
    return "Unknown time";
  }

  const date = new Date(dateValue);

  if (Number.isNaN(date.getTime())) {
    return dateValue;
  }

  return date.toLocaleString();
}

function App() {
  const [voices, setVoices] = useState([]);
  const [history, setHistory] = useState([]);

  const [selectedVoiceId, setSelectedVoiceId] = useState("");

  const [text, setText] = useState(DEFAULT_TEXT);

  const [speed, setSpeed] = useState(1);
  const [volume, setVolume] = useState(1);
  const [bass, setBass] = useState(0);

  const [style, setStyle] = useState("neutral");

  const [engine, setEngine] = useState("auto");
  const [allowFallback, setAllowFallback] = useState(true);

  const [latestGeneration, setLatestGeneration] = useState(null);

  const [initialLoading, setInitialLoading] = useState(true);

  const [generating, setGenerating] = useState(false);

  const [deletingId, setDeletingId] = useState(null);

  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const selectedVoice = useMemo(() => {
    return voices.find((voice) => String(voice.id) === String(selectedVoiceId));
  }, [voices, selectedVoiceId]);

  async function loadVoices(preferredVoiceId = null) {
    const data = await api.getVoices();

    const voiceList = Array.isArray(data) ? data : [];

    setVoices(voiceList);

    setSelectedVoiceId((currentVoiceId) => {
      const preferredId =
        preferredVoiceId !== null && preferredVoiceId !== undefined
          ? String(preferredVoiceId)
          : "";

      const preferredVoiceExists =
        preferredId &&
        voiceList.some((voice) => String(voice.id) === preferredId);

      if (preferredVoiceExists) {
        return preferredId;
      }

      const currentVoiceExists =
        currentVoiceId &&
        voiceList.some((voice) => String(voice.id) === String(currentVoiceId));

      if (currentVoiceExists) {
        return String(currentVoiceId);
      }

      if (voiceList.length > 0) {
        return String(voiceList[0].id);
      }

      return "";
    });

    return voiceList;
  }

  async function loadHistory() {
    const data = await api.getHistory();

    setHistory(Array.isArray(data) ? data : []);
  }

  async function loadApplication() {
    setInitialLoading(true);
    setError("");

    try {
      await Promise.all([loadVoices(), loadHistory()]);
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setInitialLoading(false);
    }
  }

  useEffect(() => {
    loadApplication();
  }, []);

  async function handleGenerate(event) {
    event.preventDefault();

    setError("");
    setNotice("");

    const cleanText = text.trim();

    if (!selectedVoiceId) {
      setError("Select a saved voice before generating speech.");

      return;
    }

    if (!cleanText) {
      setError("Enter a script before generating speech.");

      return;
    }

    setGenerating(true);

    try {
      const generated = await api.generateSpeech({
        voice_id: Number(selectedVoiceId),
        text: cleanText,
        speed: Number(speed),
        volume: Number(volume),
        bass: Number(bass),
        style,
        engine,
        allow_fallback: engine === "auto" ? allowFallback : false,
      });

      setLatestGeneration(generated);

      setHistory((currentHistory) => {
        const remaining = currentHistory.filter(
          (item) => item.id !== generated.id,
        );

        return [generated, ...remaining];
      });

      setNotice(
        `Narration generated successfully using ${generated.voice_name} with ${formatEngine(generated.engine_used)}.`,
      );
    } catch (generationError) {
      setError(generationError.message);
    } finally {
      setGenerating(false);
    }
  }

  async function handleDelete(generation) {
    const confirmed = window.confirm(
      "Delete this generated narration and its WAV file?",
    );

    if (!confirmed) {
      return;
    }

    setError("");
    setNotice("");
    setDeletingId(generation.id);

    try {
      await api.deleteGeneration(generation.id);

      setHistory((currentHistory) =>
        currentHistory.filter((item) => item.id !== generation.id),
      );

      if (latestGeneration?.id === generation.id) {
        setLatestGeneration(null);
      }

      setNotice("Generated narration deleted successfully.");
    } catch (deleteError) {
      setError(deleteError.message);
    } finally {
      setDeletingId(null);
    }
  }

  function resetControls() {
    setSpeed(1);
    setVolume(1);
    setBass(0);
    setEngine("auto");
    setAllowFallback(true);
    setStyle("neutral");
  }

  if (initialLoading) {
    return (
      <main className="loading-screen">
        <div className="loading-card">
          <div className="spinner" />

          <h1>AI Voice Studio</h1>

          <p>Connecting to your local voice engine...</p>
        </div>
      </main>
    );
  }

  return (
    <div className="application-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">LOCAL CREATOR TOOL</p>

          <h1>AI Voice Studio</h1>

          <p className="topbar-description">
            Generate reusable narration from your saved reference voice.
          </p>
        </div>

        <div className="engine-status">
          <span className="status-dot" />
          Backend connected
        </div>
      </header>

      <main className="dashboard">
        {(error || notice) && (
          <section
            className={
              error ? "message error-message" : "message success-message"
            }
          >
            {error || notice}
          </section>
        )}
        <VoiceLibrary
          voices={voices}
          selectedVoiceId={selectedVoiceId}
          onSelectVoice={(voiceId) =>
            setSelectedVoiceId(voiceId ? String(voiceId) : "")
          }
          onRefreshVoices={loadVoices}
          onRefreshHistory={loadHistory}
          onNotice={(message) => {
            setError("");
            setNotice(message);
          }}
          onError={(message) => {
            setNotice("");
            setError(message);
          }}
        />
        <section className="studio-grid">
          <form className="panel generator-panel" onSubmit={handleGenerate}>
            <div className="panel-heading">
              <div>
                <p className="section-label">GENERATOR</p>

                <h2>Create narration</h2>
              </div>

              <button
                type="button"
                className="text-button"
                onClick={resetControls}
              >
                Reset controls
              </button>
            </div>

            <label className="field-group">
              <span className="field-label">Select voice</span>

              <select
                value={selectedVoiceId}
                onChange={(event) => setSelectedVoiceId(event.target.value)}
              >
                {voices.length === 0 && (
                  <option value="">No saved voices available</option>
                )}

                {voices.map((voice) => (
                  <option key={voice.id} value={voice.id}>
                    {voice.voice_name}
                    {" — "}
                    {voice.language || "Mixed"}
                  </option>
                ))}
              </select>
            </label>

            {selectedVoice && (
              <div className="voice-summary">
                <div>
                  <span>Voice</span>
                  <strong>{selectedVoice.voice_name}</strong>
                </div>

                <div>
                  <span>Language</span>
                  <strong>{selectedVoice.language || "Mixed"}</strong>
                </div>

                <div>
                  <span>Reference</span>
                  <strong>
                    {selectedVoice.duration
                      ? `${selectedVoice.duration.toFixed(1)} sec`
                      : "Available"}
                  </strong>
                </div>

                <div>
                  <span>Transcript</span>
                  <strong>
                    {selectedVoice.transcript ? "Ready" : "Missing"}
                  </strong>
                </div>
              </div>
            )}

            <label className="field-group">
              <span className="field-label">Speech engine</span>

              <select
                value={engine}
                onChange={(event) => setEngine(event.target.value)}
              >
                <option value="auto">Automatic</option>
                <option value="cosyvoice">CosyVoice</option>
                <option value="indicf5">IndicF5</option>
              </select>

              <small>
                {engine === "auto"
                  ? "Choose by detected language and use fallback when enabled."
                  : engine === "cosyvoice"
                    ? "Use CosyVoice only. Explicit engine requests do not fall back."
                    : "Use IndicF5 only. Explicit engine requests do not fall back."}
              </small>
            </label>

            <label className="field-group">
              <span className="field-label">Fallback</span>

              <span>
                <input
                  type="checkbox"
                  checked={allowFallback}
                  disabled={engine !== "auto"}
                  onChange={(event) => setAllowFallback(event.target.checked)}
                />
                {" "}
                Allow the secondary engine when the automatic choice is unavailable
              </span>

              <small>
                {engine === "auto"
                  ? allowFallback
                    ? "Enabled: generation can continue with the secondary engine."
                    : "Disabled: generation stops when the primary engine fails."
                  : "Disabled because explicit engine selection is strict."}
              </small>
            </label>

            <label className="field-group">
              <div className="field-header">
                <span className="field-label">Content script</span>

                <span className="character-count">{text.length} / 10,000</span>
              </div>

              <textarea
                value={text}
                maxLength={10000}
                rows={10}
                placeholder="Paste your reel, short, lesson, or narration script here..."
                onChange={(event) => setText(event.target.value)}
              />
            </label>

            <div className="controls-grid">
              <label className="control-card">
                <div className="control-heading">
                  <span>Speed</span>
                  <strong>{Number(speed).toFixed(2)}×</strong>
                </div>

                <input
                  type="range"
                  min="0.75"
                  max="1.25"
                  step="0.05"
                  value={speed}
                  onChange={(event) => setSpeed(Number(event.target.value))}
                />

                <small>Slower for calm explanations, faster for hooks.</small>
              </label>

              <label className="control-card">
                <div className="control-heading">
                  <span>Volume</span>
                  <strong>{Number(volume).toFixed(2)}×</strong>
                </div>

                <input
                  type="range"
                  min="0.5"
                  max="1.5"
                  step="0.05"
                  value={volume}
                  onChange={(event) => setVolume(Number(event.target.value))}
                />

                <small>Adjust final loudness without re-recording.</small>
              </label>

              <label className="control-card">
                <div className="control-heading">
                  <span>Bass</span>
                  <strong>{Number(bass).toFixed(1)} dB</strong>
                </div>

                <input
                  type="range"
                  min="-6"
                  max="8"
                  step="0.5"
                  value={bass}
                  onChange={(event) => setBass(Number(event.target.value))}
                />

                <small>
                  Add subtle warmth; extreme bass can reduce clarity.
                </small>
              </label>
            </div>

            <label className="field-group">
              <span className="field-label">Voice style</span>

              <select
                value={style}
                disabled={generating}
                onChange={(event) => setStyle(event.target.value)}
              >
                {Object.entries(STYLE_LABELS).map(
                  ([styleValue, styleLabel]) => (
                    <option key={styleValue} value={styleValue}>
                      {styleLabel}
                    </option>
                  ),
                )}
              </select>

              <small>
                Select a delivery profile. Your original script and
                saved reference voice remain unchanged.
              </small>
            </label>

            <button
              type="submit"
              className="primary-button"
              disabled={generating || voices.length === 0}
            >
              {generating ? "Generating narration..." : "Generate narration"}
            </button>

            <p className="generation-note">
              Generation can take longer than the final audio duration. Keep
              both backend terminals running.
            </p>
          </form>

          <aside className="panel preview-panel">
            <p className="section-label">LATEST OUTPUT</p>

            <h2>Preview</h2>

            {latestGeneration ? (
              <div className="preview-content">
                <div className="preview-badge">
                  Generation #{latestGeneration.id}
                </div>

                <h3>{latestGeneration.voice_name}</h3>

                <p className="preview-script">{latestGeneration.text}</p>

                <audio
                  controls
                  preload="metadata"
                  src={api.audioUrl(latestGeneration)}
                />

                <div className="preview-controls">
                  <span>{latestGeneration.speed}× speed</span>

                  <span>{latestGeneration.volume}× volume</span>

                  <span>{latestGeneration.bass} dB bass</span>

                  <span>
                    Style: {formatStyle(latestGeneration.style)}
                  </span>
                </div>

                <div className="preview-controls">
                  <span>
                    Engine: {formatEngine(latestGeneration.engine_used)}
                  </span>

                  <span>
                    Language: {latestGeneration.detected_language || "Unknown"}
                  </span>

                  <span>
                    Fallback: {latestGeneration.fallback_used ? "Used" : "Not used"}
                  </span>
                </div>

                {latestGeneration.routing_reason && (
                  <p className="generation-note">
                    Routing: {latestGeneration.routing_reason}
                  </p>
                )}

                {latestGeneration.quality_warning && (
                  <div className="quality-reminder">
                    <strong>Routing quality note</strong>

                    <p>{latestGeneration.quality_warning}</p>
                  </div>
                )}

                <a
                  className="secondary-button"
                  href={api.downloadUrl(latestGeneration)}
                >
                  Download WAV
                </a>
              </div>
            ) : (
              <div className="empty-preview">
                <div className="wave-icon">≋</div>

                <h3>No new narration yet</h3>

                <p>
                  Select your voice, enter a script, and generate the first
                  preview.
                </p>
              </div>
            )}

            <div className="quality-reminder">
              <strong>Creator quality reminder</strong>

              <p>
                Listen once before publishing. Pronunciation and emotion still
                depend on the reference recording, transcript, punctuation, and
                script.
              </p>
            </div>
          </aside>
        </section>

        <section className="panel history-panel">
          <div className="panel-heading">
            <div>
              <p className="section-label">LIBRARY</p>

              <h2>Generated history</h2>
            </div>

            <button type="button" className="text-button" onClick={loadHistory}>
              Refresh history
            </button>
          </div>

          {history.length === 0 ? (
            <div className="empty-history">
              No generated narration has been saved.
            </div>
          ) : (
            <div className="history-list">
              {history.map((item) => (
                <article className="history-item" key={item.id}>
                  <div className="history-main">
                    <div className="history-title-row">
                      <strong>
                        {item.voice_name || `Voice ${item.voice_id}`}
                      </strong>

                      <span>{formatDate(item.created_at)}</span>
                    </div>

                    <p>{item.text}</p>

                    <div className="history-metadata">
                      <span>{item.speed}× speed</span>

                      <span>{item.volume}× volume</span>

                      <span>{item.bass} dB bass</span>

                      <span>
                        Style: {formatStyle(item.style)}
                      </span>

                      <span>
                        Engine: {formatEngine(item.engine_used)}
                      </span>

                      <span>
                        Fallback: {item.fallback_used ? "Used" : "Not used"}
                      </span>
                    </div>
                  </div>

                  <div className="history-actions">
                    <audio controls preload="none" src={api.audioUrl(item)} />

                    <a className="small-button" href={api.downloadUrl(item)}>
                      Download
                    </a>

                    <button
                      type="button"
                      className="small-button danger-button"
                      disabled={deletingId === item.id}
                      onClick={() => handleDelete(item)}
                    >
                      {deletingId === item.id ? "Deleting..." : "Delete"}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
