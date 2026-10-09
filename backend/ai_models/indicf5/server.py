from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import (
    FastAPI,
    HTTPException,
)
from fastapi.responses import FileResponse

from .config import (
    DEVICE,
    MODEL_ID,
    OUTPUT_DIRECTORY,
    SERVICE_NAME,
    SERVICE_VERSION,
)
from .engine import IndicF5Engine
from .schemas import (
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    ModelStatusResponse,
)

engine = IndicF5Engine()
generation_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncIterator[None]:
    print("=" * 80)
    print("STARTING INDICF5 GPU SERVICE")
    print("=" * 80)

    await asyncio.to_thread(engine.load)

    app.state.engine = engine

    print(
        "Model loaded:",
        engine.loaded,
    )
    print(
        "Device:",
        engine.device,
    )
    print(
        "CUDA parameters:",
        engine.cuda_parameters,
    )
    print(
        "Load seconds:",
        engine.load_seconds,
    )

    try:
        yield
    finally:
        print("Stopping IndicF5 GPU service...")

        await asyncio.to_thread(engine.shutdown)


app = FastAPI(
    title=SERVICE_NAME,
    version=SERVICE_VERSION,
    lifespan=lifespan,
)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get(
    "/health",
    response_model=HealthResponse,
)
async def health() -> HealthResponse:
    data = engine.health_data()

    status = "healthy" if data["model_loaded"] else "starting"

    return HealthResponse(
        status=status,
        service=SERVICE_NAME,
        version=SERVICE_VERSION,
        model_id=MODEL_ID,
        **data,
    )


@app.get(
    "/model/status",
    response_model=ModelStatusResponse,
)
async def model_status() -> ModelStatusResponse:
    return ModelStatusResponse(
        model_id=MODEL_ID,
        loaded=engine.loaded,
        device=str(engine.device),
        total_parameters=(engine.total_parameters),
        cpu_parameters=(engine.cpu_parameters),
        cuda_parameters=(engine.cuda_parameters),
        load_seconds=(engine.load_seconds),
    )


@app.post(
    "/generate",
    response_model=GenerateResponse,
)
async def generate(
    request: GenerateRequest,
) -> GenerateResponse:
    if not engine.loaded:
        raise HTTPException(
            status_code=503,
            detail=("IndicF5 model is not loaded."),
        )

    async with generation_lock:
        try:
            result = await asyncio.to_thread(
                engine.generate,
                text=request.text,
                reference_audio=(request.reference_audio),
                reference_transcript=(request.reference_transcript),
            )

        except (
            ValueError,
            FileNotFoundError,
        ) as error:
            raise HTTPException(
                status_code=400,
                detail=str(error),
            ) from error

        except RuntimeError as error:
            raise HTTPException(
                status_code=500,
                detail=str(error),
            ) from error

        except Exception as error:
            raise HTTPException(
                status_code=500,
                detail=(
                    "IndicF5 generation failed: " f"{type(error).__name__}: " f"{error}"
                ),
            ) from error

    return GenerateResponse(
        status="completed",
        engine="indicf5",
        device=str(engine.device),
        language=request.language,
        output_file=(result["output_file"]),
        output_path=(result["output_path"]),
        output_url=("/outputs/" + result["output_file"]),
        generation_seconds=(result["generation_seconds"]),
        audio_duration_seconds=(result["audio_duration_seconds"]),
        real_time_factor=(result["real_time_factor"]),
        sample_rate=(result["sample_rate"]),
        channels=(result["channels"]),
        peak_cuda_mb=(result["peak_cuda_mb"]),
    )


@app.get(
    "/outputs/{filename}",
)
async def get_output(
    filename: str,
) -> FileResponse:
    safe_name = Path(filename).name

    if safe_name != filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid output filename.",
        )

    output_path = (OUTPUT_DIRECTORY / safe_name).resolve()

    if output_path.parent != OUTPUT_DIRECTORY.resolve():
        raise HTTPException(
            status_code=400,
            detail="Invalid output path.",
        )

    if not output_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Output file not found.",
        )

    return FileResponse(
        path=str(output_path),
        media_type="audio/wav",
        filename=safe_name,
    )