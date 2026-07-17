"""Config fields that MUST be identical between backend and worker for
tasks to flow at all: the Redis connection they both talk to, and the
shared secret the worker authenticates task updates with.

Defined once here and inherited by both backend/core/config.py's and
worker/config.py's Settings classes, instead of being hand-duplicated in
both files - where a typo'd default, or an update made to one side but
not the other, would silently break task delivery with no error pointing
at why.

Inheriting the field *definitions* here doesn't by itself guarantee the
*values* two separately-deployed containers actually see are identical -
that still depends on both being handed the same environment at deploy
time. Two more layers cover that:
  - docker-compose.yml's `x-shared-env` YAML anchor, so the compose file
    itself can't specify two different literal values for these fields
    across the backend/worker services.
  - worker/main.py's startup check against GET /api/v1/worker/ping,
    which catches drift even when neither of the above applies (e.g. the
    two processes are deployed on separate hosts with independently
    managed secrets, well outside what shared Python code or one compose
    file can enforce).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class SharedSettings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="ignore",
    )

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_QUEUE_NAME: str = "gridforge_tasks"

    # No safe default on purpose, same reasoning as JWT_SECRET_KEY in
    # backend/core/config.py - override in .env for any deployment that
    # isn't purely local/throwaway.
    WORKER_API_KEY: str = "dev-only-insecure-worker-key-change-me"
