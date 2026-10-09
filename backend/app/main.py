from fastapi import FastAPI

from app.core.config import settings

from app.database.connection import Base
from app.database.connection import engine

from app.api.voice import router as voice_router
from app.api.speech import router as speech_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="AI Voice Studio Backend",
)

app.include_router(voice_router)
app.include_router(speech_router)


@app.get("/")
def home():
    return {
        "message": "AI Voice Studio Backend Running",
        "status": "OK",
    }


@app.get("/health")
def health():
    return {
        "database": "Connected",
        "server": "Running",
    }