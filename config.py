import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = "club-sportif-2026"
    DB_CONFIG = {
        "host": "localhost",
        "user": "club_app",
        "password": os.getenv("DB_PASSWORD"),
        "database": "club_sport",
    }
