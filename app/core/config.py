import os
import secrets
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "LocuSearch"
    PROJECT_VERSION: str = "0.1.0"

    PROJECT_URL_V1: str = "/api/v1"

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:////Users/kunjjoshi/Downloads/PROJECTS/LocuSearch/LocuSearch-app/loc.sqlite3")

    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    USER_ID_FORMAT: str = "{:05d}"

    AWS_ACCESS_KEY: Optional[str] = os.getenv("AWS_ACCESS_KEY")
    AWS_SECRET_KEY: Optional[str] = os.getenv("AWS_SECRET_KEY")
    AWS_REGION: str = "us-east-2"
    AWS_BUCKET_NAME: str = "locubucket"

    WEAVIATE_URL: str = "http://localhost:8080"

settings = Settings()


