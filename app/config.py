"""Application configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

APP_ENV: str = os.getenv("APP_ENV", "development")
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
ROOT_PATH: str = os.getenv("ROOT_PATH", "")
API_VERSION: str = os.getenv("API_VERSION", "v1")
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
