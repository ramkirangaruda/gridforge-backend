from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
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
    # Left unset by default so the validator below can derive it from the
    # actual (possibly env-overridden) UPLOADS_DIR. Set DB_PATH explicitly
    # (env var or .env) to still override it independently.
    DB_PATH: Optional[Path] = None

    # Worker
    MAX_EXECUTION_TIME: int = 300 # in seconds

    # Frontend
    FRONTEND_URL: Optional[str] = None

    @model_validator(mode="after")
    def _default_db_path(self) -> "Settings":
        if self.DB_PATH is None:
            self.DB_PATH = self.UPLOADS_DIR / "tasks_db.json"
        return self

settings = Settings()
