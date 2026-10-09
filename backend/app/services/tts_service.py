from datetime import datetime

from pathlib import Path

import shutil

import subprocess

import tempfile

import uuid



from sqlalchemy.orm import Session



from app.ai.preprocess import TextPreprocessor

from app.ai.segmenter import TextSegmenter

from app.core.config import settings

from app.audio.style_profiles import resolve_style_controls

from app.database.models import GeneratedAudio

from app.database.models import Voice

from app.services.engine_router import engine_router

from app.services.segment_router import segment_router

from app.services.segmented_synthesis import segmented_synthesis





class TTSService:



    ALLOWED_STYLES = {

        "neutral",

        "professional",

        "energetic",

        "calm",

        "storytelling",

    }



    def __init__(self):



        self.output_folder = Path(settings.OUTPUT_FOLDER).resolve()



        self.output_folder.mkdir(

            parents=True,

            exist_ok=True,

        )



    # ========================================================

    # File helpers

    # ========================================================



    @staticmethod

    def generate_filename() -> str:



        return f"{uuid.uuid4()}.wav"



    @staticmethod

    def create_temp_wav_path() -> Path:



        return Path(tempfile.gettempdir()) / f"{uuid.uuid4()}.wav"



    @staticmethod

    def delete_file_safely(

        file_path: Path | None,

    ) -> None:



        if file_path is None:

            return



        try:



            if file_path.exists():

                file_path.unlink()



        except OSError as error:



            print("Warning: Could not delete file " f"{file_path}: {error}")



    # ========================================================

    # Control validation

    # ========================================================



    @staticmethod

    def validate_controls(

        speed: float,

        volume: float,

        bass: float,

    ) -> None:



        if not 0.5 <= speed <= 2.0:



            raise ValueError("Speed must be between 0.5 and 2.0.")



        if not 0.1 <= volume <= 3.0:



            raise ValueError("Volume must be between 0.1 and 3.0.")



        if not -20.0 <= bass <= 20.0:



            raise ValueError("Bass must be between -20 and 20 dB.")



    # ========================================================

    # Reference-audio preparation

    # ========================================================



    def prepare_reference_audio(

        self,

        reference_audio: Path,

    ) -> Path:

        """

        Create a normalized temporary copy of the complete

        synchronized reference WAV.



        This method must not seek, trim, crop, or change the

        temporal content because the stored transcript describes

        the complete stored reference.

        """



        resolved_reference = reference_audio.resolve()



        if not resolved_reference.exists():

            raise FileNotFoundError(

                "The synchronized reference audio "

                "was not found:\n"

                f"{resolved_reference}"

            )



        if not resolved_reference.is_file():

            raise ValueError(

                "The synchronized reference path "

                "is not a file:\n"

                f"{resolved_reference}"

            )



        if resolved_reference.stat().st_size <= 0:

            raise ValueError("The synchronized reference audio " "file is empty.")



        temp_file = (

            Path(tempfile.gettempdir())

            / ("synchronized_reference_" + uuid.uuid4().hex + ".wav")

        ).resolve()



        command = [

            "ffmpeg",

            "-y",

            "-nostdin",

            "-loglevel",

            "error",

            "-i",

            str(resolved_reference),

            "-map",

            "0:a:0",

            "-vn",

            "-ar",

            "24000",

            "-ac",

            "1",

            "-c:a",

            "pcm_s16le",

            str(temp_file),

        ]



        try:

            subprocess.run(

                command,

                check=True,

                capture_output=True,

                text=True,

            )



        except subprocess.CalledProcessError as error:

            self.delete_file_safely(temp_file)



            ffmpeg_error = (

                error.stderr.strip() if error.stderr else "Unknown FFmpeg error."

            )



            raise RuntimeError(

                "Could not normalize the complete "

                "synchronized reference audio.\n"

                f"FFmpeg error: {ffmpeg_error}"

            ) from error



        if not temp_file.exists():

            raise RuntimeError(

                "FFmpeg completed, but the temporary "

                "synchronized reference was not created."

            )



        if temp_file.stat().st_size <= 0:

            self.delete_file_safely(temp_file)



            raise RuntimeError("The temporary synchronized reference " "file is empty.")



        return temp_file



    # ========================================================

    # Final audio processing

    # ========================================================



    def apply_audio_controls(

        self,

        raw_audio: Path,

        final_audio: Path,

        volume: float,

        bass: float,

        speed: float = 1.0,

        apply_speed: bool = False,

        presence_gain_db: float = 0.0,
        presence_frequency_hz: int = 2800,
        presence_q: float = 1.2,
    ) -> None:



        if not raw_audio.exists():



            raise FileNotFoundError(

                f"Raw generated audio is missing:\n{raw_audio}"

            )



        filters: list[str] = []



        # CosyVoice applies speed natively. IndicF5 currently

        # generates at native speed, so FFmpeg applies atempo

        # only when the router reports that speed was not applied.

        if (

            apply_speed

            and abs(speed - 1.0) >= 0.001

        ):



            filters.append(

                f"atempo={speed:.4f}"

            )



        # Candidate B style-presence processing.
        if abs(presence_gain_db) >= 0.01:
            if not 100 <= presence_frequency_hz <= 10000:
                raise ValueError(
                    "Presence frequency must be between "
                    "100 and 10000 Hz."
                )

            if not 0.1 <= presence_q <= 10.0:
                raise ValueError(
                    "Presence Q must be between 0.1 and 10.0."
                )

            if not -6.0 <= presence_gain_db <= 6.0:
                raise ValueError(
                    "Presence gain must be between "
                    "-6.0 and 6.0 dB."
                )

            filters.append(
                "equalizer="
                f"f={presence_frequency_hz}:"
                "t=q:"
                f"w={presence_q:.2f}:"
                f"g={presence_gain_db:.2f}"
            )

        # Bass is measured in decibels.

        if abs(bass) >= 0.01:



            filters.append(

                f"bass=g={bass:.2f}:f=100"

            )



        # Volume is a multiplier:

        # 1.0 = original, 0.5 = half, 1.2 = louder.

        if abs(volume - 1.0) >= 0.001:



            filters.append(

                f"volume={volume:.4f}"

            )



        print("\nAUDIO CONTROLS")

        print("-" * 80)

        print("Speed  :", speed)

        print(

            "Apply speed in FFmpeg:",

            apply_speed,

        )

        print("Volume :", volume)

        print("Bass   :", bass)



        if not filters:



            print(

                "No shared FFmpeg processing required."

            )



            shutil.move(

                str(raw_audio),

                str(final_audio),

            )



            return



        # Preserve the existing limiter protection after

        # shared processing.

        if (
            volume > 1.001
            or bass > 0.01
            or presence_gain_db > 1.5
        ):
            filters.append(
                "alimiter="
                "limit=0.95:"
                "level=false:"
                "latency=1"
            )



        filter_chain = ",".join(

            filters

        )



        print("Filter :", filter_chain)



        command = [

            "ffmpeg",

            "-y",

            "-nostdin",

            "-loglevel",

            "error",

            "-i",

            str(raw_audio),

            "-af",

            filter_chain,

            "-ar",

            "24000",

            "-ac",

            "1",

            "-c:a",

            "pcm_s16le",

            str(final_audio),

        ]



        try:



            subprocess.run(

                command,

                check=True,

                capture_output=True,

                text=True,

            )



        except subprocess.CalledProcessError as error:



            self.delete_file_safely(

                final_audio

            )



            ffmpeg_error = (

                error.stderr.strip()

                if error.stderr

                else "Unknown FFmpeg error."

            )



            raise RuntimeError(

                "Could not apply shared audio controls.\n"

                f"FFmpeg error: {ffmpeg_error}"

            ) from error



        if not final_audio.exists():



            raise RuntimeError(

                "The processed output WAV "

                "was not created."

            )



        if final_audio.stat().st_size <= 0:



            self.delete_file_safely(

                final_audio

            )



            raise RuntimeError(

                "The processed output WAV is empty."

            )



    # ========================================================

    # Speech generation

    # ========================================================



    def generate_speech(

        self,

        db: Session,

        voice_id: int,

        text: str,

        speed: float = 1.0,

        volume: float = 1.0,

        bass: float = 0.0,

        style: str = "neutral",

        requested_engine: str = "auto",

        allow_fallback: bool = True,

    ) -> dict:



        print("\n" + "=" * 80)

        print("TTS SERVICE START")

        print("=" * 80)



        clean_text = (

            TextPreprocessor.validate_api_text(

                text

            )

        )



        romanized_telugu_signal = (

            TextPreprocessor.is_probably_romanized_telugu(

                clean_text

            )

        )



        clean_engine = (

            requested_engine

            .strip()

            .lower()

        )



        clean_style = (

            style

            .strip()

            .lower()

        )



        if not clean_text:



            raise ValueError(

                "Speech text cannot be empty."

            )



        if (

            clean_engine

            not in engine_router.ALLOWED_ENGINES

        ):



            raise ValueError(

                "Engine must be one of: "

                "auto, cosyvoice, indicf5."

            )



        if clean_style not in self.ALLOWED_STYLES:

            allowed_styles = ", ".join(

                sorted(self.ALLOWED_STYLES)

            )



            raise ValueError(

                "Style must be one of: "

                f"{allowed_styles}."

            )



        self.validate_controls(

            speed=speed,

            volume=volume,

            bass=bass,

        )



        style_controls = resolve_style_controls(

            style=clean_style,

            speed=speed,

            volume=volume,

            bass=bass,

        )



        effective_speed = (

            style_controls.effective_speed

        )



        effective_volume = (

            style_controls.effective_volume

        )



        effective_bass = (

            style_controls.effective_bass

        )



        self.validate_controls(

            speed=effective_speed,

            volume=effective_volume,

            bass=effective_bass,

        )



        print("\nSTYLE PROFILE")

        print("-" * 80)

        print("Style            :", clean_style)

        print("Requested Speed  :", speed)

        print("Effective Speed  :", effective_speed)

        print("Requested Volume :", volume)

        print("Effective Volume :", effective_volume)

        print("Requested Bass   :", bass)

        print("Effective Bass   :", effective_bass)



        text_segments = TextSegmenter.segment(

            clean_text

        )



        routing_decisions = (

            segment_router.plan_segments(

                text_segments,

                requested_engine=clean_engine,

                allow_fallback=allow_fallback,

            )

        )



        synthesis_text = "\n".join(

            segment.synthesis_text

            for segment in text_segments

        )



        prepared_cosyvoice_reference: Path | None = None

        raw_output_path: Path | None = None

        final_output_path: Path | None = None



        try:



            print(f"Voice ID        : {voice_id}")

            print(f"History Text    : {clean_text}")

            print(f"Synthesis Text  : {synthesis_text}")

            print(

                "Romanized Telugu:",

                romanized_telugu_signal,

            )

            print(f"Speed           : {speed}")

            print(f"Volume          : {volume}")

            print(f"Bass            : {bass}")



            print(f"Style           : {clean_style}")

            print(f"Requested Engine: {clean_engine}")

            print(f"Allow Fallback  : {allow_fallback}")



            # ------------------------------------------------

            # Fetch selected voice

            # ------------------------------------------------



            voice = (

                db.query(Voice)

                .filter(

                    Voice.id == voice_id

                )

                .first()

            )



            print("\nDATABASE LOOKUP")

            print("-" * 80)



            if voice is None:



                raise ValueError(

                    f"Voice with ID {voice_id} "

                    "was not found."

                )



            print(

                "Voice Name :",

                voice.voice_name,

            )



            print(

                "WAV File   :",

                voice.wav_filename,

            )



            if not voice.wav_filename:



                raise ValueError(

                    "The selected voice does not "

                    "have a reference WAV."

                )



            if not voice.transcript:



                raise ValueError(

                    "The selected voice does not "

                    "have a reference transcript."

                )



            clean_transcript = (

                TextPreprocessor.normalize(

                    voice.transcript

                )

            )



            if not clean_transcript:



                raise ValueError(

                    "The selected voice transcript "

                    "is empty."

                )



            # ------------------------------------------------

            # Resolve the original synchronized reference

            # ------------------------------------------------



            reference_audio = (

                Path(settings.VOICE_FOLDER)

                / voice.wav_filename

            ).resolve()



            print("\nREFERENCE AUDIO")

            print("-" * 80)

            print(reference_audio)

            print(

                "Exists:",

                reference_audio.exists(),

            )



            if not reference_audio.exists():



                raise FileNotFoundError(

                    "Reference audio was not found:\n"

                    f"{reference_audio}"

                )



            # ------------------------------------------------

            # Resolve routing plan

            # ------------------------------------------------



            routing_summary = (

                segment_router.summarize(

                    routing_decisions

                )

            )



            detected_languages = (

                routing_summary[

                    "languages"

                ]

            )



            routing_plan: list[str] = []



            for decision in routing_decisions:

                for engine_name in decision.engine_plan:

                    if engine_name not in routing_plan:

                        routing_plan.append(

                            engine_name

                        )



            print("\nROUTING PREPARATION")

            print("-" * 80)

            print(

                "Segment Count:",

                len(routing_decisions),

            )

            print(

                "Detected Languages:",

                detected_languages,

            )

            print(

                "Combined Engine Plan:",

                routing_plan,

            )



            # IndicF5 must receive the original WAV inside

            # backend/app/voices. CosyVoice receives a normalized

            # temporary reference whenever it is in the plan.

            cosyvoice_reference = reference_audio



            if "cosyvoice" in routing_plan:



                print(

                    "Preparing CosyVoice reference..."

                )



                prepared_cosyvoice_reference = (

                    self.prepare_reference_audio(

                        reference_audio

                    )

                )



                cosyvoice_reference = (

                    prepared_cosyvoice_reference

                )



                print(

                    "CosyVoice Reference:",

                    cosyvoice_reference,

                )



            else:



                print(

                    "CosyVoice reference preparation "

                    "not required."

                )



            # ------------------------------------------------

            # Prepare output paths

            # ------------------------------------------------



            output_name = self.generate_filename()



            final_output_path = (

                self.output_folder

                / output_name

            ).resolve()



            raw_output_path = (

                self.create_temp_wav_path()

            )



            print("\nOUTPUT PATHS")

            print("-" * 80)

            print(

                "Raw   :",

                raw_output_path,

            )

            print(

                "Final :",

                final_output_path,

            )



            # ------------------------------------------------

            # Generate through the selected engine

            # ------------------------------------------------



            print(

                "\nCALLING SEGMENTED SYNTHESIS..."

            )

            print("-" * 80)



            routing_result = (

                segmented_synthesis.generate(

                    decisions=routing_decisions,

                    requested_engine=clean_engine,

                    original_reference_audio=str(

                        reference_audio

                    ),

                    cosyvoice_reference_audio=str(

                        cosyvoice_reference

                    ),

                    prompt_text=clean_transcript,

                    output_path=str(

                        raw_output_path

                    ),

                )

            )



            if not raw_output_path.exists():



                raise RuntimeError(

                    "The selected engine returned "

                    "successfully, but raw audio is missing."

                )



            if raw_output_path.stat().st_size <= 0:



                raise RuntimeError(

                    "The selected engine produced "

                    "an empty raw WAV file."

                )



            print("\nROUTING RESULT")

            print("-" * 80)

            print(

                "Engine Used:",

                routing_result[

                    "engine_used"

                ],

            )

            print(

                "Fallback Used:",

                routing_result[

                    "fallback_used"

                ],

            )

            print(

                "Routing Reason:",

                routing_result[

                    "routing_reason"

                ],

            )



            speed_applied_by_engine = bool(

                routing_result.get(

                    "speed_applied_by_engine",

                    False,

                )

            )



            # ------------------------------------------------

            # Apply shared controls exactly once

            # ------------------------------------------------



            self.apply_audio_controls(

                raw_audio=raw_output_path,

                final_audio=final_output_path,

                volume=effective_volume,

                bass=effective_bass,

                speed=effective_speed,

                apply_speed=(

                    True

                ),

                presence_gain_db=style_controls.profile.presence_gain_db,
                presence_frequency_hz=style_controls.profile.presence_frequency_hz,
                presence_q=style_controls.profile.presence_q,
            )



            # ------------------------------------------------

            # Verify final output

            # ------------------------------------------------



            if not final_output_path.exists():



                raise RuntimeError(

                    "Final generated WAV is missing."

                )



            final_size = (

                final_output_path

                .stat()

                .st_size

            )



            if final_size <= 0:



                raise RuntimeError(

                    "Final generated WAV is empty."

                )



            print("\nFINAL AUDIO COMPLETE")

            print("-" * 80)

            print(

                "Generated:",

                final_size,

                "bytes",

            )



            # ------------------------------------------------

            # Save history only after final processing succeeds

            # ------------------------------------------------



            created_at = datetime.utcnow()



            generated_audio = GeneratedAudio(

                voice_id=voice.id,

                text=clean_text,

                output_filename=output_name,

                speed=speed,

                volume=volume,

                bass=bass,

                style=clean_style,

                engine_requested=(

                    routing_result[

                        "engine_requested"

                    ]

                ),

                engine_used=(

                    routing_result[

                        "engine_used"

                    ]

                ),

                fallback_used=bool(

                    routing_result[

                        "fallback_used"

                    ]

                ),

                routing_reason=(

                    routing_result[

                        "routing_reason"

                    ]

                ),

                created_at=created_at,

            )



            db.add(

                generated_audio

            )



            db.flush()



            result = {

                "id": generated_audio.id,

                "voice_id": voice.id,

                "voice_name": voice.voice_name,

                "text": clean_text,

                "output_filename": output_name,

                "speed": speed,

                "volume": volume,

                "bass": bass,

                "style": clean_style,

                "created_at": created_at,

                "engine_requested": (

                    routing_result[

                        "engine_requested"

                    ]

                ),

                "engine_used": (

                    routing_result[

                        "engine_used"

                    ]

                ),

                "detected_language": (

                    routing_result[

                        "detected_language"

                    ]

                ),

                "fallback_used": (

                    routing_result[

                        "fallback_used"

                    ]

                ),

                "routing_reason": (

                    routing_result[

                        "routing_reason"

                    ]

                ),

                "quality_warning": (

                    routing_result.get(

                        "quality_warning"

                    )

                ),

            }



            db.commit()



            print("\nHISTORY RECORD SAVED")

            print("-" * 80)

            print(

                "Generation ID:",

                generated_audio.id,

            )

            print(

                "Output File:",

                output_name,

            )

            print(

                "Engine Used:",

                routing_result[

                    "engine_used"

                ],

            )

            print("=" * 80)



            return result



        except Exception:



            db.rollback()



            self.delete_file_safely(

                final_output_path

            )



            raise



        finally:



            self.delete_file_safely(

                prepared_cosyvoice_reference

            )



            self.delete_file_safely(

                raw_output_path

            )







tts_service = TTSService()

