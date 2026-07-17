from pydantic_settings import SettingsConfigDict
from pydantic import model_validator
from pathlib import Path
from typing import Optional

from shared.config import SharedSettings

class Settings(SharedSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra='ignore'
    )
    PROJECT_NAME: str = "GridForge"
    API_V1_STR: str = "/api/v1"

    # Gates the FRONTEND_URL/CORS startup check in main.py. Only the exact
    # value "development" (the default) is treated as safe to run without
    # FRONTEND_URL set; anything else - "production", "staging", a typo
    # like "prod" - is treated as requiring it. That's deliberately the
    # opposite of an allow-list: forgetting to set this, or misspelling it,
    # should fail closed (refuse to start with wildcard CORS) rather than
    # fail open (silently allow it).
    ENVIRONMENT: str = "development"

    # API Port
    API_PORT: int = 8000

    # REDIS_HOST/PORT/DB/QUEUE_NAME and WORKER_API_KEY come from
    # SharedSettings (see shared/config.py) - not redeclared here.

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
