import os
from dotenv import load_dotenv

load_dotenv()


class Settings:

    APP_NAME = os.getenv("APP_NAME")

    VERSION = os.getenv("VERSION")

    HOST = os.getenv("HOST")

    PORT = int(os.getenv("PORT"))

    DATABASE_URL = os.getenv("DATABASE_URL")

    VOICE_FOLDER = os.getenv("VOICE_FOLDER")

    OUTPUT_FOLDER = os.getenv("OUTPUT_FOLDER")

    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE"))

    ALLOWED_EXTENSIONS = [
        extension.strip().lower()
        for extension in os.getenv("ALLOWED_EXTENSIONS").split(",")
    ]

    LOG_LEVEL = os.getenv("LOG_LEVEL")


settings = Settings()