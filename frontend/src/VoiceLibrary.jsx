import { useRef, useState } from "react";

import { api } from "./api";

const DEFAULT_LANGUAGE = "Mixed Telugu-English";

function formatDuration(value) {
  const duration = Number(value);

  if (!Number.isFinite(duration)) {
    return "Unknown";
  }

  return `${duration.toFixed(1)} sec`;
}

function VoiceLibrary({
  voices,
  selectedVoiceId,
  onSelectVoice,
  onRefreshVoices,
  onRefreshHistory,
  onNotice,
  onError,
}) {
  const fileInputRef = useRef(null);

  const [voiceName, setVoiceName] = useState("");
  const [language, setLanguage] = useState(DEFAULT_LANGUAGE);
  const [referenceFile, setReferenceFile] = useState(null);

  const [uploading, setUploading] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [savingId, setSavingId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  const [editDraft, setEditDraft] = useState({
    voice_name: "",
    language: "",
    transcript: "",
  });

  function beginEdit(voice) {
    setEditingId(voice.id);

    setEditDraft({
      voice_name: voice.voice_name || "",
      language: voice.language || "Mixed",
      transcript: voice.transcript || "",
    });
  }

  function cancelEdit() {
    setEditingId(null);

    setEditDraft({
      voice_name: "",
      language: "",
      transcript: "",
    });
  }

  async function handleUpload(event) {
    event.preventDefault();

    onError("");
    onNotice("");

    const cleanName = voiceName.trim();
    const cleanLanguage = language.trim() || "Mixed";

    if (!cleanName) {
      onError("Enter a name for the voice profile.");
      return;
    }

    if (!referenceFile) {
      onError("Choose a reference audio file.");
      return;
    }

    setUploading(true);

    try {
      const uploadedVoice = await api.uploadVoice({
        voiceName: cleanName,
        language: cleanLanguage,
        file: referenceFile,
      });

      await onRefreshVoices(uploadedVoice.id);

      onSelectVoice(uploadedVoice.id);
      beginEdit(uploadedVoice);

      setVoiceName("");
      setLanguage(DEFAULT_LANGUAGE);
      setReferenceFile(null);

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      onNotice(
        "Voice uploaded and transcribed. Review and correct the transcript before generating narration.",
      );
    } catch (error) {
      onError(error.message);
    } finally {
      setUploading(false);
    }
  }

  async function handleSave(voice) {
    onError("");
    onNotice("");

    const cleanName = editDraft.voice_name.trim();
    const cleanLanguage = editDraft.language.trim();
    const cleanTranscript = editDraft.transcript.trim();

    if (!cleanName) {
      onError("Voice name cannot be empty.");
      return;
    }

    if (!cleanLanguage) {
      onError("Language cannot be empty.");
      return;
    }

    if (!cleanTranscript) {
      onError("Transcript cannot be empty.");
      return;
    }

    const payload = {};

    if (cleanName !== voice.voice_name) {
      payload.voice_name = cleanName;
    }

    if (cleanLanguage !== voice.language) {
      payload.language = cleanLanguage;
    }

    if (cleanTranscript !== (voice.transcript || "")) {
      payload.transcript = cleanTranscript;
    }

    if (Object.keys(payload).length === 0) {
      onNotice("No changes were detected in this voice profile.");

      cancelEdit();
      return;
    }

    setSavingId(voice.id);

    try {
      await api.updateVoice(voice.id, payload);

      await onRefreshVoices(voice.id);

      cancelEdit();

      onNotice("Voice profile and transcript updated successfully.");
    } catch (error) {
      onError(error.message);
    } finally {
      setSavingId(null);
    }
  }

  async function handleDelete(voice) {
    const confirmed = window.confirm(
      [
        `Delete "${voice.voice_name}"?`,
        "",
        "This also deletes:",
        "• the uploaded reference files",
        "• generated narration history for this voice",
        "• related generated WAV files",
        "",
        "This action cannot be undone.",
      ].join("\n"),
    );

    if (!confirmed) {
      return;
    }

    onError("");
    onNotice("");
    setDeletingId(voice.id);

    try {
      const result = await api.deleteVoice(voice.id);

      await Promise.all([onRefreshVoices(), onRefreshHistory()]);

      if (String(selectedVoiceId) === String(voice.id)) {
        onSelectVoice("");
      }

      onNotice(result.message || "Voice deleted successfully.");
    } catch (error) {
      onError(error.message);
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <section className="panel voice-library-panel">
      <div className="panel-heading">
        <div>
          <p className="section-label">VOICE LIBRARY</p>
          <h2>Reference voices</h2>
        </div>

        <div className="voice-count">
          {voices.length} {voices.length === 1 ? "voice" : "voices"}
        </div>
      </div>

      <form className="voice-upload-form" onSubmit={handleUpload}>
        <div className="voice-upload-grid">
          <label className="field-group">
            <span className="field-label">Voice profile name</span>

            <input
              type="text"
              maxLength={100}
              value={voiceName}
              placeholder="Swarup - Energetic"
              onChange={(event) => setVoiceName(event.target.value)}
            />
          </label>

          <label className="field-group">
            <span className="field-label">Language</span>

            <input
              type="text"
              list="voice-language-options"
              maxLength={50}
              value={language}
              onChange={(event) => setLanguage(event.target.value)}
            />

            <datalist id="voice-language-options">
              <option value="English" />
              <option value="Telugu" />
              <option value="Mixed" />
              <option value="Mixed Telugu-English" />
            </datalist>
          </label>

          <label className="field-group">
            <span className="field-label">Reference audio</span>

            <input
              ref={fileInputRef}
              type="file"
              accept="audio/*,.wav,.mp3,.m4a"
              onChange={(event) =>
                setReferenceFile(event.target.files?.[0] || null)
              }
            />
          </label>
        </div>

        <div className="upload-footer">
          <p className="upload-help">
            Use one clear speaker, minimal background noise, no music, and one
            consistent speaking style.
          </p>

          <button
            type="submit"
            className="compact-primary-button"
            disabled={uploading}
          >
            {uploading
              ? "Uploading and transcribing..."
              : "Upload reference voice"}
          </button>
        </div>
      </form>

      {voices.length === 0 ? (
        <div className="empty-history">
          No reference voices have been uploaded.
        </div>
      ) : (
        <div className="voice-cards">
          {voices.map((voice) => {
            const selected = String(selectedVoiceId) === String(voice.id);

            const editing = editingId === voice.id;

            return (
              <article
                key={voice.id}
                className={
                  selected ? "voice-card voice-card-selected" : "voice-card"
                }
              >
                <div className="voice-card-header">
                  <div>
                    <button
                      type="button"
                      className="voice-select-button"
                      onClick={() => onSelectVoice(voice.id)}
                    >
                      {selected ? "Selected" : "Select voice"}
                    </button>

                    <h3>{voice.voice_name}</h3>

                    <p>
                      {voice.language || "Mixed"}
                      {" • "}
                      {formatDuration(voice.duration)}
                      {" • "}
                      {voice.sample_rate} Hz
                    </p>
                  </div>

                  <div className="voice-card-actions">
                    <button
                      type="button"
                      className="small-button"
                      onClick={() =>
                        editing ? cancelEdit() : beginEdit(voice)
                      }
                    >
                      {editing ? "Cancel" : "Edit profile"}
                    </button>

                    <button
                      type="button"
                      className="small-button danger-button"
                      disabled={deletingId === voice.id}
                      onClick={() => handleDelete(voice)}
                    >
                      {deletingId === voice.id ? "Deleting..." : "Delete"}
                    </button>
                  </div>
                </div>

                <audio
                  controls
                  preload="none"
                  src={api.referenceAudioUrl(voice.id)}
                />

                {!editing && (
                  <div className="voice-card-transcript">
                    <strong>Reference transcript</strong>

                    <p>{voice.transcript || "Transcript missing."}</p>
                  </div>
                )}

                {editing && (
                  <div className="voice-edit-form">
                    <div className="two-column-fields">
                      <label className="field-group">
                        <span className="field-label">Voice name</span>

                        <input
                          type="text"
                          maxLength={100}
                          value={editDraft.voice_name}
                          onChange={(event) =>
                            setEditDraft((current) => ({
                              ...current,
                              voice_name: event.target.value,
                            }))
                          }
                        />
                      </label>

                      <label className="field-group">
                        <span className="field-label">Language</span>

                        <input
                          type="text"
                          maxLength={50}
                          value={editDraft.language}
                          onChange={(event) =>
                            setEditDraft((current) => ({
                              ...current,
                              language: event.target.value,
                            }))
                          }
                        />
                      </label>
                    </div>

                    <label className="field-group">
                      <div className="field-header">
                        <span className="field-label">
                          Exact reference transcript
                        </span>

                        <span className="character-count">
                          {editDraft.transcript.length}
                          {" / 10,000"}
                        </span>
                      </div>

                      <textarea
                        rows={7}
                        maxLength={10000}
                        value={editDraft.transcript}
                        onChange={(event) =>
                          setEditDraft((current) => ({
                            ...current,
                            transcript: event.target.value,
                          }))
                        }
                      />
                    </label>

                    <p className="warning-text">
                      Write exactly what is spoken in the reference audio. Do
                      not rewrite it as a polished narration script.
                    </p>

                    <div className="inline-actions">
                      <button
                        type="button"
                        className="small-button"
                        onClick={cancelEdit}
                      >
                        Cancel
                      </button>

                      <button
                        type="button"
                        className="compact-primary-button"
                        disabled={savingId === voice.id}
                        onClick={() => handleSave(voice)}
                      >
                        {savingId === voice.id ? "Saving..." : "Save changes"}
                      </button>
                    </div>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

export default VoiceLibrary;