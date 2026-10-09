from __future__ import annotations

import re
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent

APP_PATH = (
    PROJECT_ROOT
    / "frontend"
    / "src"
    / "App.jsx"
)


def read_source(
    path: Path,
) -> str:
    return path.read_text(
        encoding="utf-8-sig",
    )


def write_source(
    path: Path,
    source: str,
) -> None:
    path.write_text(
        source,
        encoding="utf-8",
    )


def replace_once(
    source: str,
    old: str,
    new: str,
    label: str,
) -> str:
    count = source.count(old)

    if count != 1:
        raise RuntimeError(
            f"{label}: expected exactly one "
            f"occurrence, found {count}."
        )

    return source.replace(
        old,
        new,
        1,
    )


source = read_source(
    APP_PATH
)


# ============================================================
# Style labels
# ============================================================

if "const STYLE_LABELS = {" not in source:
    engine_labels_pattern = re.compile(
        r"const ENGINE_LABELS = \{\n"
        r".*?"
        r"\n\};\n",
        re.DOTALL,
    )

    match = engine_labels_pattern.search(
        source
    )

    if match is None:
        raise RuntimeError(
            "ENGINE_LABELS block was not found."
        )

    style_labels_block = '''
const STYLE_LABELS = {
  neutral: "Neutral",
  professional: "Professional",
  energetic: "Energetic",
  calm: "Calm",
  storytelling: "Storytelling",
};
'''

    source = (
        source[:match.end()]
        + style_labels_block
        + source[match.end():]
    )


# ============================================================
# Style formatting
# ============================================================

if "function formatStyle(" not in source:
    format_engine_pattern = re.compile(
        r"function formatEngine\(engineValue\) \{\n"
        r".*?"
        r"\n\}\n",
        re.DOTALL,
    )

    match = format_engine_pattern.search(
        source
    )

    if match is None:
        raise RuntimeError(
            "formatEngine function was not found."
        )

    format_style_block = '''
function formatStyle(styleValue) {
  return STYLE_LABELS[styleValue] || STYLE_LABELS.neutral;
}
'''

    source = (
        source[:match.end()]
        + format_style_block
        + source[match.end():]
    )


# ============================================================
# React style state
# ============================================================

if (
    'const [style, setStyle] = '
    'useState("neutral");'
    not in source
):
    old_state_block = '''  const [bass, setBass] = useState(0);

  const [engine, setEngine] = useState("auto");
'''

    new_state_block = '''  const [bass, setBass] = useState(0);

  const [style, setStyle] = useState("neutral");

  const [engine, setEngine] = useState("auto");
'''

    source = replace_once(
        source,
        old_state_block,
        new_state_block,
        "Insert style state",
    )


# ============================================================
# Generation request payload
# ============================================================

if "        style,\n" not in source:
    old_payload_block = '''        bass: Number(bass),
        engine,
'''

    new_payload_block = '''        bass: Number(bass),
        style,
        engine,
'''

    source = replace_once(
        source,
        old_payload_block,
        new_payload_block,
        "Insert style into generation payload",
    )


# ============================================================
# Reset style to neutral
# ============================================================

if '    setStyle("neutral");' not in source:
    reset_pattern = re.compile(
        r"(?P<start>"
        r"  function resetControls\(\) \{\n"
        r")"
        r"(?P<body>.*?)"
        r"(?P<end>\n  \})",
        re.DOTALL,
    )

    match = reset_pattern.search(
        source
    )

    if match is None:
        raise RuntimeError(
            "resetControls function was not found."
        )

    reset_body = match.group(
        "body"
    ).rstrip()

    updated_reset = (
        match.group("start")
        + reset_body
        + '\n    setStyle("neutral");'
        + match.group("end")
    )

    source = (
        source[:match.start()]
        + updated_reset
        + source[match.end():]
    )


# ============================================================
# Style selector UI
# ============================================================

if (
    '<span className="field-label">'
    "Voice style</span>"
    not in source
):
    submit_marker = '''            <button
              type="submit"
              className="primary-button"
'''

    style_selector = '''            <label className="field-group">
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

'''

    source = replace_once(
        source,
        submit_marker,
        style_selector + submit_marker,
        "Insert frontend style selector",
    )


# ============================================================
# Latest-generation style display
# ============================================================

latest_style_marker = (
    "Style: "
    "{formatStyle(latestGeneration.style)}"
)

if latest_style_marker not in source:
    old_latest_block = '''                  <span>{latestGeneration.bass} dB bass</span>
                </div>
'''

    new_latest_block = '''                  <span>{latestGeneration.bass} dB bass</span>

                  <span>
                    Style: {formatStyle(latestGeneration.style)}
                  </span>
                </div>
'''

    source = replace_once(
        source,
        old_latest_block,
        new_latest_block,
        "Display latest-generation style",
    )


# ============================================================
# History style display
# ============================================================

history_style_marker = (
    "Style: "
    "{formatStyle(item.style)}"
)

if history_style_marker not in source:
    old_history_block = '''                      <span>{item.bass} dB bass</span>

                      <span>
                        Engine: {formatEngine(item.engine_used)}
'''

    new_history_block = '''                      <span>{item.bass} dB bass</span>

                      <span>
                        Style: {formatStyle(item.style)}
                      </span>

                      <span>
                        Engine: {formatEngine(item.engine_used)}
'''

    source = replace_once(
        source,
        old_history_block,
        new_history_block,
        "Display history style",
    )


write_source(
    APP_PATH,
    source,
)


updated = read_source(
    APP_PATH
)

required_markers = [
    "const STYLE_LABELS = {",
    'neutral: "Neutral"',
    'professional: "Professional"',
    'energetic: "Energetic"',
    'calm: "Calm"',
    'storytelling: "Storytelling"',
    "function formatStyle(styleValue)",
    'const [style, setStyle] = useState("neutral");',
    "        style,",
    '    setStyle("neutral");',
    '<span className="field-label">Voice style</span>',
    "value={style}",
    "setStyle(event.target.value)",
    "Object.entries(STYLE_LABELS)",
    latest_style_marker,
    history_style_marker,
]

for marker in required_markers:
    if marker not in updated:
        raise RuntimeError(
            "Missing frontend style marker: "
            f"{marker}"
        )

if updated.count(
    'const [style, setStyle] = useState("neutral");'
) != 1:
    raise RuntimeError(
        "Style state was inserted more than once."
    )

if updated.count(
    "        style,\n"
) != 1:
    raise RuntimeError(
        "Generation payload style occurrence "
        "is not exactly one."
    )

print(
    "Milestone 10.7D-2 frontend "
    "style selector integration: APPLIED"
)
