from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Always resolve .env relative to this file (backend/app/config.py → backend/.env)
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database (psycopg3 dialect: postgresql+psycopg://)
    database_url: str = "postgresql+psycopg://localhost:5432/cognify"

    # LLM
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash-lite"
    hf_token: str = ""  # HuggingFace token for Aryabhata-1.0

    # Vector DB
    pinecone_api_key: str = ""
    pinecone_index_name: str = "cognify-questions"

    # Supermemory
    supermemory_api_key: str = ""

    # Web search
    tavily_api_key: str = ""

    # App
    app_env: str = "development"
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
