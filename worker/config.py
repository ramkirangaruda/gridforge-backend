from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra='ignore'
    )

    PROJECT_NAME: str = "GridForge Worker"
    
    # API
    API_BASE_URL: str = "http://localhost:8000/api/v1"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_QUEUE_NAME: str = "gridforge_tasks"

    # Storage
    WORKSPACES_DIR: Path = Path.cwd() / "uploads"

    # Docker
    DOCKER_IMAGE: str = "gridforge-exec:latest"
    DOCKER_TIMEOUT: int = 300 # seconds
    DOCKER_MEM_LIMIT: str = "512m"
    DOCKER_CPU_LIMIT: float = 1.0

    # Auth - must match the backend's WORKER_API_KEY
    WORKER_API_KEY: str = "dev-only-insecure-worker-key-change-me"

settings = Settings()
