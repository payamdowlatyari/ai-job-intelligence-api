"""Application configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

APP_ENV: str = os.getenv("APP_ENV", "development")
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
ROOT_PATH: str = os.getenv("ROOT_PATH", "")
