import os

from dotenv import load_dotenv


class Config:
    def __init__(self):
        load_dotenv()

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///check8.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

