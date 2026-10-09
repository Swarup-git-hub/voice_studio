from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import relationship

from datetime import datetime

from app.database.connection import Base


class Voice(Base):
    __tablename__ = "voices"

    id = Column(Integer, primary_key=True, index=True)

    voice_name = Column(String, nullable=False)


    original_filename = Column(String)

    stored_filename = Column(String)

    wav_filename = Column(String)
    language = Column(String, default="Mixed")
    duration = Column(Float, default=0)
    sample_rate = Column(Integer, default=16000)
    transcript = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    generated_audio = relationship(
        "GeneratedAudio",
        back_populates="voice",
        cascade="all, delete",
    )


class GeneratedAudio(Base):
    __tablename__ = "generated_audio"

    id = Column(Integer, primary_key=True, index=True)

    voice_id = Column(Integer, ForeignKey("voices.id"))

    text = Column(String)

    output_filename = Column(String)

    speed = Column(Float, default=1.0)

    bass = Column(Float, default=0)

    volume = Column(Float, default=1.0)

    engine_requested = Column(
        String,
        nullable=False,
        default="legacy",
    )

    engine_used = Column(
        String,
        nullable=False,
        default="legacy",
    )

    fallback_used = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    routing_reason = Column(
        String,
        nullable=False,
        default="legacy_record",
    )

    style = Column(
        String,
        nullable=False,
        default="neutral",
        server_default="neutral",
    )

    created_at = Column(DateTime, default=datetime.utcnow)

    voice = relationship(
        "Voice",
        back_populates="generated_audio",
    )
