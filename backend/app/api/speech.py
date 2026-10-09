from pathlib import Path

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi.responses import FileResponse

from sqlalchemy.orm import joinedload
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.models import GeneratedAudio
from app.database.schemas import GeneratedAudioDeleteResponse
from app.database.schemas import GeneratedAudioResponse
from app.database.schemas import GenerateSpeechRequest
from app.database.schemas import GenerateSpeechResponse
from app.database.session import get_db
from app.services.tts_service import tts_service
from app.services.engine_router import (
    EngineGenerationError,
)
from app.services.engine_router import (
    EngineUnavailableError,
)


router = APIRouter(
    prefix="/speech",
    tags=["Speech"],
)


OUTPUT_FOLDER = Path(
    settings.OUTPUT_FOLDER
).resolve()


# ============================================================
# Helpers
# ============================================================

def get_output_path(
    output_filename: str,
) -> Path:

    output_path = (
        OUTPUT_FOLDER / output_filename
    ).resolve()

    # Prevent a manipulated database filename from escaping
    # the configured outputs directory.
    if (
        output_path.parent != OUTPUT_FOLDER
        and OUTPUT_FOLDER not in output_path.parents
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid generated audio path.",
        )

    return output_path


def get_generation_or_404(
    db: Session,
    generation_id: int,
) -> GeneratedAudio:

    generation = (
        db.query(GeneratedAudio)
        .options(
            joinedload(GeneratedAudio.voice)
        )
        .filter(
            GeneratedAudio.id == generation_id
        )
        .first()
    )

    if generation is None:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Generated audio with ID "
                f"{generation_id} was not found."
            ),
        )

    return generation


def serialize_generation(
    generation: GeneratedAudio,
) -> dict:

    voice_name = None

    if generation.voice is not None:
        voice_name = generation.voice.voice_name

    return {
        "id": generation.id,
        "voice_id": generation.voice_id,
        "voice_name": voice_name,
        "text": generation.text,
        "output_filename": generation.output_filename,
        "speed": generation.speed,
        "volume": generation.volume,
        "bass": generation.bass,
        "style": generation.style,
        "created_at": generation.created_at,
        "engine_requested": (
            generation.engine_requested
        ),
        "engine_used": generation.engine_used,
        "fallback_used": bool(
            generation.fallback_used
        ),
        "routing_reason": (
            generation.routing_reason
        ),
        "audio_url": (
            f"/speech/history/"
            f"{generation.id}/audio"
        ),
        "download_url": (
            f"/speech/history/"
            f"{generation.id}/download"
        ),
    }


# ============================================================
# Basic Route
# ============================================================

@router.get("/")
def home():

    return {
        "message": "Speech API Ready",
        "history_enabled": True,
    }


# ============================================================
# Generate Speech
# ============================================================

@router.post(
    "/generate",
    response_model=GenerateSpeechResponse,
)
def generate(
    request: GenerateSpeechRequest,
    db: Session = Depends(get_db),
):

    try:

        result = tts_service.generate_speech(
            db=db,
            voice_id=request.voice_id,
            text=request.text,
            speed=request.speed,
            volume=request.volume,
            bass=request.bass,
            style=request.style,
            requested_engine=request.engine,
            allow_fallback=request.allow_fallback,
        )

        generation_id = result["id"]

        return {
            "status": "success",
            **result,
            "audio_url": (
                f"/speech/history/"
                f"{generation_id}/audio"
            ),
            "download_url": (
                f"/speech/history/"
                f"{generation_id}/download"
            ),
        }

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except FileNotFoundError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    except EngineUnavailableError as error:

        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from error

    except EngineGenerationError as error:

        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error

    except HTTPException:

        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error


# ============================================================
# Generation History
# ============================================================

@router.get(
    "/history",
    response_model=list[GeneratedAudioResponse],
)
def list_generation_history(
    offset: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
    ),
    db: Session = Depends(get_db),
):

    generations = (
        db.query(GeneratedAudio)
        .options(
            joinedload(GeneratedAudio.voice)
        )
        .order_by(
            GeneratedAudio.created_at.desc(),
            GeneratedAudio.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        serialize_generation(generation)
        for generation in generations
    ]


@router.get(
    "/history/{generation_id}",
    response_model=GeneratedAudioResponse,
)
def get_generation_history_item(
    generation_id: int,
    db: Session = Depends(get_db),
):

    generation = get_generation_or_404(
        db=db,
        generation_id=generation_id,
    )

    return serialize_generation(generation)


# ============================================================
# Playback
# ============================================================

@router.get(
    "/history/{generation_id}/audio"
)
def play_generated_audio(
    generation_id: int,
    db: Session = Depends(get_db),
):

    generation = get_generation_or_404(
        db=db,
        generation_id=generation_id,
    )

    output_path = get_output_path(
        generation.output_filename
    )

    if not output_path.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "The history record exists, but its "
                "generated WAV file is missing."
            ),
        )

    return FileResponse(
        path=str(output_path),
        media_type="audio/wav",
        headers={
            "Content-Disposition": (
                f'inline; filename="'
                f'{output_path.name}"'
            )
        },
    )


# ============================================================
# Download
# ============================================================

@router.get(
    "/history/{generation_id}/download"
)
def download_generated_audio(
    generation_id: int,
    db: Session = Depends(get_db),
):

    generation = get_generation_or_404(
        db=db,
        generation_id=generation_id,
    )

    output_path = get_output_path(
        generation.output_filename
    )

    if not output_path.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "The history record exists, but its "
                "generated WAV file is missing."
            ),
        )

    return FileResponse(
        path=str(output_path),
        media_type="audio/wav",
        filename=output_path.name,
    )


# ============================================================
# Delete Generation
# ============================================================

@router.delete(
    "/history/{generation_id}",
    response_model=GeneratedAudioDeleteResponse,
)
def delete_generated_audio(
    generation_id: int,
    db: Session = Depends(get_db),
):

    generation = get_generation_or_404(
        db=db,
        generation_id=generation_id,
    )

    output_path = get_output_path(
        generation.output_filename
    )

    pending_delete_path: Path | None = None

    try:

        # Temporarily rename the file before changing the DB.
        # This lets us restore it if the DB commit fails.
        if output_path.exists():

            pending_delete_path = output_path.with_name(
                output_path.name + ".delete_pending"
            )

            if pending_delete_path.exists():
                pending_delete_path.unlink()

            output_path.replace(
                pending_delete_path
            )

        db.delete(generation)
        db.commit()

    except Exception as error:

        db.rollback()

        # Restore the WAV if database deletion failed.
        if (
            pending_delete_path is not None
            and pending_delete_path.exists()
        ):

            pending_delete_path.replace(
                output_path
            )

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not delete the generated "
                f"audio record: {error}"
            ),
        ) from error

    audio_file_deleted = False

    if (
        pending_delete_path is not None
        and pending_delete_path.exists()
    ):

        try:

            pending_delete_path.unlink()
            audio_file_deleted = True

        except OSError:

            audio_file_deleted = False

    return {
        "status": "success",
        "generation_id": generation_id,
        "database_record_deleted": True,
        "audio_file_deleted": audio_file_deleted,
        "message": (
            "Generated audio history record deleted."
            if audio_file_deleted
            else (
                "History record deleted. The WAV file "
                "was already missing or could not be removed."
            )
        ),
    }