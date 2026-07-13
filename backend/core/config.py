from pydantic_settings import BaseSettings
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra='ignore'
    )
    PROJECT_NAME: str = "GridForge"
    API_V1_STR: str = "/api/v1"
    
    # API Port
    API_PORT: int = 8000

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_QUEUE_NAME: str = "gridforge_tasks"

    # Storage
    UPLOADS_DIR: Path = Path.cwd() / "uploads"
    DB_PATH: Path = UPLOADS_DIR / "tasks_db.json"
    
    # Worker
    MAX_EXECUTION_TIME: int = 300 # in seconds

    # Frontend
    FRONTEND_URL: Optional[str] = None

settings = Settings()

settings = Settings()
