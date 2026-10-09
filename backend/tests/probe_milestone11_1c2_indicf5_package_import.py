from __future__ import annotations

import importlib


module = importlib.import_module(
    "ai_models.indicf5.server"
)

if not hasattr(
    module,
    "app",
):
    raise RuntimeError(
        "IndicF5 server module does not expose FastAPI app."
    )

print(
    "IndicF5 package import: PASSED"
)

print(
    "FastAPI app found:",
    hasattr(
        module,
        "app",
    ),
)
