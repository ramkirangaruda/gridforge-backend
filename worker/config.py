import sys
from pathlib import Path

# worker/main.py and its siblings use unqualified imports (`from config
# import settings`), which only works with worker/ itself on sys.path -
# that's how the process is normally run (`python worker/main.py`, or the
# WORKDIR /app/worker in worker/Dockerfile.worker). But shared/ lives one
# level up (a sibling of worker/, both under the repo root locally or
# /app in the container), so it's NOT on sys.path by that mechanism.
# Adding it here, relative to this file rather than assuming a CWD or an
# externally-set PYTHONPATH, makes `from shared.config import
# SharedSettings` below work regardless of how/from-where this process
# was launched.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic_settings import SettingsConfigDict  # noqa: E402
from shared.config import SharedSettings  # noqa: E402

class Settings(SharedSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra='ignore'
    )

    PROJECT_NAME: str = "GridForge Worker"

    # API
    API_BASE_URL: str = "http://localhost:8000/api/v1"

    # REDIS_HOST/PORT/DB/QUEUE_NAME and WORKER_API_KEY come from
    # SharedSettings (see shared/config.py) - not redeclared here.

    # Storage
    WORKSPACES_DIR: Path = Path.cwd() / "uploads"

    # Docker
    DOCKER_IMAGE: str = "gridforge-exec:latest"
    DOCKER_TIMEOUT: int = 300 # seconds
    DOCKER_MEM_LIMIT: str = "512m"
    DOCKER_CPU_LIMIT: float = 1.0

    # Zip bomb guard: refuse to extract if the sum of ZipInfo.file_size
    # across all entries (i.e. the archive's *declared* uncompressed size)
    # exceeds this, regardless of how small the zip itself is on disk.
    # Mirrors the backend's MAX_UPLOAD_SIZE_BYTES in spirit, not value -
    # a 100MB compressed upload could still legitimately decompress a bit
    # larger, so this is intentionally its own separate cap.
    MAX_UNCOMPRESSED_ZIP_SIZE: int = 100 * 1024 * 1024  # 100MB

settings = Settings()
