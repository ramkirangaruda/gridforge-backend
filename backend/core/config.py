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

    # SQLAlchemy connection string. Left unset by default so the validator
    # below derives a SQLite URL from DB_PATH. Override with a Postgres (or
    # other) URL if this ever needs to scale past a single SQLite file -
    # nothing else in the app needs to change, since task_service.py only
    # talks to SQLAlchemy's engine/session API.
    DATABASE_URL: Optional[str] = None

    # Worker
    MAX_EXECUTION_TIME: int = 300 # in seconds

    # Uploads / quota
    MAX_UPLOAD_SIZE_BYTES: int = 100 * 1024 * 1024   # 100MB per zip
    MAX_USER_STORAGE_BYTES: int = 500 * 1024 * 1024  # 500MB total per user

    # Frontend
    FRONTEND_URL: Optional[str] = None

    # Auth
    # No safe default on purpose - override in .env for any deployment that
    # isn't purely local/throwaway, since anyone who knows this value can
    # forge valid login tokens.
    JWT_SECRET_KEY: str = "dev-only-insecure-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    # Shared secret the worker presents on POST /task/{id}/update, since the
    # worker process has no per-user JWT of its own. Must match worker's
    # WORKER_API_KEY.
    WORKER_API_KEY: str = "dev-only-insecure-worker-key-change-me"

    @model_validator(mode="after")
    def _default_db_path(self) -> "Settings":
        if self.DB_PATH is None:
            self.DB_PATH = self.UPLOADS_DIR / "tasks.db"
        if self.DATABASE_URL is None:
            # sqlite:///<absolute-path>, forward slashes even on Windows -
            # SQLAlchemy's SQLite dialect expects POSIX-style separators.
            self.DATABASE_URL = f"sqlite:///{self.DB_PATH.resolve().as_posix()}"
        return self

settings = Settings()
