import traceback

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import UploadFile
from fastapi.responses import FileResponse

from sqlalchemy.orm import Session

from app.database.schemas import VoiceDeleteResponse
from app.database.schemas import VoiceResponse
from app.database.schemas import VoiceUpdate
from app.database.session import get_db
from app.services.voice_service import delete_voice
from app.services.voice_service import get_all_voices
from app.services.voice_service import get_reference_audio_path
from app.services.voice_service import get_voice
from app.services.voice_service import save_uploaded_voice
from app.services.voice_service import update_voice_profile

router = APIRouter(
    prefix="/voice",
    tags=["Voice"],
)


# ============================================================
# Basic Route
# ============================================================


@router.get("/")
def home():

    return {
        "message": "Voice API Ready",
        "transcript_editing": True,
        "reference_playback": True,
    }


# ============================================================
# Upload
# ============================================================


@router.post(
    "/upload",
    response_model=VoiceResponse,
    status_code=201,
)
async def upload_voice(
    voice_name: str = Form(...),
    language: str = Form("Mixed"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):

    try:

        voice = save_uploaded_voice(
            db=db,
            voice_name=voice_name,
            language=language,
            file=file,
        )

        return voice

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:

        print("\n" + "=" * 80)
        print("VOICE UPLOAD ERROR")
        print("=" * 80)

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error


# ============================================================
# List and Details
# ============================================================


@router.get(
    "/list",
    response_model=list[VoiceResponse],
)
def list_voices(
    db: Session = Depends(get_db),
):

    return get_all_voices(db)


@router.get(
    "/{voice_id}",
    response_model=VoiceResponse,
)
def get_voice_details(
    voice_id: int,
    db: Session = Depends(get_db),
):

    voice = get_voice(
        db=db,
        voice_id=voice_id,
    )

    if voice is None:

        raise HTTPException(
            status_code=404,
            detail="Voice not found.",
        )

    return voice


# ============================================================
# Reference Playback
# ============================================================


@router.get("/{voice_id}/audio")
def play_reference_audio(
    voice_id: int,
    db: Session = Depends(get_db),
):

    voice = get_voice(
        db=db,
        voice_id=voice_id,
    )

    if voice is None:

        raise HTTPException(
            status_code=404,
            detail="Voice not found.",
        )

    try:

        reference_path = get_reference_audio_path(voice)

    except FileNotFoundError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    return FileResponse(
        path=str(reference_path),
        media_type="audio/wav",
        headers={
            "Content-Disposition": (f'inline; filename="' f'{reference_path.name}"')
        },
    )


# ============================================================
# Update Voice Profile
# ============================================================


@router.put(
    "/{voice_id}",
    response_model=VoiceResponse,
)
def update_voice(
    voice_id: int,
    data: VoiceUpdate,
    db: Session = Depends(get_db),
):

    try:

        voice = update_voice_profile(
            db=db,
            voice_id=voice_id,
            voice_name=data.voice_name,
            language=data.language,
            transcript=data.transcript,
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    if voice is None:

        raise HTTPException(
            status_code=404,
            detail="Voice not found.",
        )

    return voice


# ============================================================
# Delete Voice
# ============================================================


@router.delete(
    "/{voice_id}",
    response_model=VoiceDeleteResponse,
)
def remove_voice(
    voice_id: int,
    db: Session = Depends(get_db),
):

    try:

        result = delete_voice(
            db=db,
            voice_id=voice_id,
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=("Could not safely delete the " f"voice: {error}"),
        ) from error

    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Voice not found.",
        )

    return result