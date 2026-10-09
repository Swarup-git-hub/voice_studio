from pathlib import Path
import shutil
import uuid

from fastapi import UploadFile
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from app.audio.analyzer import AudioAnalyzer
from app.audio.converter import convert_to_wav
from app.audio.reference_preparer import prepare_reference_audio
from app.audio.transcriber import transcriber
from app.core.config import settings
from app.database.models import Voice
from app.utils.file_utils import generate_unique_filename

VOICE_FOLDER = Path(settings.VOICE_FOLDER).resolve()

OUTPUT_FOLDER = Path(settings.OUTPUT_FOLDER).resolve()


VOICE_FOLDER.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_FOLDER.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# File Helpers
# ============================================================


def delete_file_safely(
    file_path: Path | None,
) -> bool:
    """
    Delete a file without crashing the main operation.

    Returns True when a file was deleted.
    Returns False when the path was missing or deletion failed.
    """

    if file_path is None:
        return False

    try:
        if file_path.exists():
            file_path.unlink()
            return True

    except OSError as error:
        print("Warning: Could not delete file " f"{file_path}: {error}")

    return False


def unique_paths(
    paths: list[Path],
) -> list[Path]:
    """
    Remove duplicate paths while preserving their order.
    """

    results: list[Path] = []
    seen: set[Path] = set()

    for file_path in paths:
        resolved_path = file_path.resolve()

        if resolved_path in seen:
            continue

        seen.add(resolved_path)
        results.append(resolved_path)

    return results


def stage_files_for_deletion(
    file_paths: list[Path],
) -> tuple[
    list[tuple[Path, Path]],
    int,
]:
    """
    Rename files to a temporary deletion name before a
    destructive database operation.

    This allows the files to be restored when the database
    transaction fails.
    """

    staged_files: list[tuple[Path, Path]] = []

    files_not_found = 0

    try:
        for original_path in unique_paths(file_paths):
            if not original_path.exists():
                files_not_found += 1
                continue

            pending_path = original_path.with_name(
                original_path.name + "." + uuid.uuid4().hex + ".delete_pending"
            )

            original_path.replace(pending_path)

            staged_files.append(
                (
                    original_path,
                    pending_path,
                )
            )

        return staged_files, files_not_found

    except Exception:
        restore_staged_files(staged_files)

        raise


def restore_staged_files(
    staged_files: list[tuple[Path, Path]],
) -> None:
    """
    Restore files that were temporarily staged for deletion.
    """

    for original_path, pending_path in reversed(staged_files):
        try:
            if pending_path.exists():
                pending_path.replace(original_path)

        except OSError as error:
            print("Warning: Could not restore staged " f"file {pending_path}: {error}")


def finalize_staged_files(
    staged_files: list[tuple[Path, Path]],
) -> int:
    """
    Permanently delete files after the database transaction
    has succeeded.
    """

    files_deleted = 0

    for _, pending_path in staged_files:
        if delete_file_safely(pending_path):
            files_deleted += 1

    return files_deleted


# ============================================================
# Upload Voice
# ============================================================


def save_uploaded_voice(
    db: Session,
    voice_name: str,
    language: str,
    file: UploadFile,
):
    """
    Save an uploaded voice using exact reference
    synchronization.

    Pipeline:

    original upload
        -> complete converted WAV
        -> permanent synchronized 8-15 second reference
        -> validation of that exact reference
        -> transcription of that exact reference
        -> one database record containing the matching
           reference filename and transcript
    """

    clean_voice_name = voice_name.strip()

    clean_language = language.strip() if language else "Mixed"

    if not clean_voice_name:
        raise ValueError("Voice name cannot be empty.")

    if len(clean_voice_name) > 100:
        raise ValueError("Voice name cannot exceed " "100 characters.")

    if not clean_language:
        clean_language = "Mixed"

    if len(clean_language) > 50:
        raise ValueError("Language cannot exceed " "50 characters.")

    original_filename = file.filename if file.filename else "reference_audio"

    extension = Path(original_filename).suffix.lower()

    if extension not in settings.ALLOWED_EXTENSIONS:
        raise ValueError(f"{extension or 'This file type'} " "is not supported.")

    unique_filename = generate_unique_filename(original_filename)

    save_path = (VOICE_FOLDER / Path(unique_filename).name).resolve()

    converted_path: Path | None = None
    reference_path: Path | None = None

    database_committed = False

    try:
        # ----------------------------------------------------
        # 1. Save the original uploaded file
        # ----------------------------------------------------

        with open(
            save_path,
            "wb",
        ) as buffer:
            shutil.copyfileobj(
                file.file,
                buffer,
            )

        if not save_path.exists():
            raise RuntimeError("The uploaded reference file " "was not saved.")

        if save_path.stat().st_size <= 0:
            raise ValueError("The uploaded reference file is empty.")

        print("\n" + "=" * 80)
        print("VOICE UPLOAD RECEIVED")
        print("=" * 80)
        print("Original file :", original_filename)
        print("Stored file   :", save_path)

        # ----------------------------------------------------
        # 2. Convert the complete upload to WAV
        # ----------------------------------------------------

        converted_path = Path(convert_to_wav(str(save_path))).resolve()

        if not converted_path.exists():
            raise RuntimeError(
                "Audio conversion completed, but "
                "the converted WAV file was not created."
            )

        if converted_path.stat().st_size <= 0:
            raise RuntimeError("The converted WAV file is empty.")

        print("\nComplete converted WAV:")
        print(converted_path)

        # ----------------------------------------------------
        # 3. Create one permanent synchronized reference
        # ----------------------------------------------------

        preparation = prepare_reference_audio(converted_path)

        reference_path = preparation.path.resolve()

        if not reference_path.exists():
            raise RuntimeError("The synchronized reference WAV " "was not created.")

        if reference_path.stat().st_size <= 0:
            raise RuntimeError("The synchronized reference WAV is empty.")

        print("\n" + "=" * 80)
        print("SYNCHRONIZED REFERENCE CREATED")
        print("=" * 80)

        print(
            "Source start :",
            f"{preparation.source_start:.3f}s",
        )

        print(
            "Source end   :",
            f"{preparation.source_end:.3f}s",
        )

        print(
            "Duration     :",
            f"{preparation.duration:.3f}s",
        )

        print(
            "Reference WAV:",
            reference_path,
        )

        # ----------------------------------------------------
        # 4. Validate the exact synchronized reference
        # ----------------------------------------------------

        analyzer = AudioAnalyzer(str(reference_path))

        validation_result = analyzer.validate()

        if not validation_result["valid"]:
            raise ValueError(", ".join(validation_result["errors"]))

        audio_info = validation_result["info"]

        prepared_duration = float(audio_info["duration"])

        prepared_sample_rate = int(audio_info["sample_rate"])

        if prepared_duration < 7.9:
            raise ValueError(
                "The synchronized reference is too short. "
                "At least 8 seconds are required."
            )

        if prepared_duration > 15.2:
            raise ValueError(
                "The synchronized reference is too long. "
                "The maximum expected length is 15 seconds."
            )

        if prepared_sample_rate != 24000:
            raise ValueError(
                "The synchronized reference must use " "a 24,000 Hz sample rate."
            )

        # ----------------------------------------------------
        # 5. Transcribe that exact synchronized reference
        # ----------------------------------------------------

        print("\nTranscribing synchronized reference...")

        transcript = transcriber.transcribe(str(reference_path))

        clean_transcript = transcript.strip() if transcript else ""

        if not clean_transcript:
            raise ValueError(
                "The synchronized reference could not "
                "be transcribed. Use clear continuous "
                "speech with minimal background noise."
            )

        print("\nSynchronized transcript:")
        print(clean_transcript)

        # ----------------------------------------------------
        # 6. Save the matching reference and transcript
        # ----------------------------------------------------

        voice = Voice(
            voice_name=clean_voice_name,
            original_filename=original_filename,
            stored_filename=save_path.name,
            wav_filename=reference_path.name,
            language=clean_language,
            duration=prepared_duration,
            sample_rate=prepared_sample_rate,
            transcript=clean_transcript,
        )

        db.add(voice)

        db.commit()
        database_committed = True

        db.refresh(voice)

        # ----------------------------------------------------
        # 7. Delete only the complete temporary converted WAV
        #
        # Keep:
        #   - original uploaded file
        #   - permanent synchronized reference WAV
        # ----------------------------------------------------

        if converted_path != save_path and converted_path != reference_path:
            delete_file_safely(converted_path)

        print("\n" + "=" * 80)
        print("REFERENCE AND TRANSCRIPT SYNCHRONIZED")
        print("=" * 80)
        print("Voice ID       :", voice.id)
        print("Voice name     :", voice.voice_name)
        print("Reference file :", voice.wav_filename)
        print("Duration       :", voice.duration)
        print("Sample rate    :", voice.sample_rate)
        print("Transcript     :", voice.transcript)

        return voice

    except Exception:
        # A committed database record must retain its files.
        # Cleaning files after a successful commit could
        # leave the database pointing to missing audio.
        if database_committed:
            raise

        db.rollback()

        cleanup_paths = [
            save_path,
        ]

        if converted_path is not None:
            cleanup_paths.append(converted_path)

        if reference_path is not None:
            cleanup_paths.append(reference_path)

        for cleanup_path in unique_paths(cleanup_paths):
            delete_file_safely(cleanup_path)

        raise


# ============================================================
# Voice Queries
# ============================================================


def get_all_voices(
    db: Session,
):
    return (
        db.query(Voice)
        .order_by(
            Voice.created_at.desc(),
            Voice.id.desc(),
        )
        .all()
    )


def get_voice(
    db: Session,
    voice_id: int,
):
    return db.query(Voice).filter(Voice.id == voice_id).first()


def get_voice_with_history(
    db: Session,
    voice_id: int,
):
    return (
        db.query(Voice)
        .options(joinedload(Voice.generated_audio))
        .filter(Voice.id == voice_id)
        .first()
    )


def get_reference_audio_path(
    voice: Voice,
) -> Path:
    if not voice.wav_filename:
        raise FileNotFoundError(
            "The selected voice does not have " "a reference WAV file."
        )

    reference_path = (VOICE_FOLDER / Path(voice.wav_filename).name).resolve()

    if not reference_path.exists():
        raise FileNotFoundError(
            "Reference WAV file was not found:\n" f"{reference_path}"
        )

    return reference_path


# ============================================================
# Update Voice Profile
# ============================================================


def update_voice_profile(
    db: Session,
    voice_id: int,
    voice_name: str | None = None,
    language: str | None = None,
    transcript: str | None = None,
):
    voice = get_voice(
        db=db,
        voice_id=voice_id,
    )

    if voice is None:
        return None

    fields_updated = False

    if voice_name is not None:
        clean_voice_name = voice_name.strip()

        if not clean_voice_name:
            raise ValueError("Voice name cannot be empty.")

        if len(clean_voice_name) > 100:
            raise ValueError("Voice name cannot exceed " "100 characters.")

        voice.voice_name = clean_voice_name

        fields_updated = True

    if language is not None:
        clean_language = language.strip()

        if not clean_language:
            raise ValueError("Language cannot be empty.")

        if len(clean_language) > 50:
            raise ValueError("Language cannot exceed " "50 characters.")

        voice.language = clean_language

        fields_updated = True

    if transcript is not None:
        clean_transcript = transcript.strip()

        if not clean_transcript:
            raise ValueError("Transcript cannot be empty.")

        if len(clean_transcript) > 10000:
            raise ValueError("Transcript cannot exceed " "10,000 characters.")

        voice.transcript = clean_transcript

        fields_updated = True

    if not fields_updated:
        raise ValueError("No voice fields were provided " "for update.")

    try:
        db.commit()
        db.refresh(voice)

        return voice

    except Exception:
        db.rollback()
        raise


# ============================================================
# Delete Voice and Related Files
# ============================================================


def delete_voice(
    db: Session,
    voice_id: int,
):
    voice = get_voice_with_history(
        db=db,
        voice_id=voice_id,
    )

    if voice is None:
        return None

    voice_name = voice.voice_name

    generated_audio_records_deleted = len(voice.generated_audio)

    candidate_paths: list[Path] = []

    if voice.stored_filename:
        candidate_paths.append(
            (VOICE_FOLDER / Path(voice.stored_filename).name).resolve()
        )

    if voice.wav_filename:
        candidate_paths.append((VOICE_FOLDER / Path(voice.wav_filename).name).resolve())

    for generated_audio in voice.generated_audio:
        if not generated_audio.output_filename:
            continue

        candidate_paths.append(
            (OUTPUT_FOLDER / Path(generated_audio.output_filename).name).resolve()
        )

    staged_files, files_not_found = stage_files_for_deletion(candidate_paths)

    try:
        db.delete(voice)

        db.commit()

    except Exception:
        db.rollback()

        restore_staged_files(staged_files)

        raise

    files_deleted = finalize_staged_files(staged_files)

    return {
        "status": "success",
        "voice_id": voice_id,
        "voice_name": voice_name,
        "generated_audio_records_deleted": generated_audio_records_deleted,
        "files_deleted": files_deleted,
        "files_not_found": files_not_found,
        "message": (
            "Voice, reference files, and related "
            "generated narration history were deleted."
        ),
    }