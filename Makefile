# Convenience targets for running GridForge outside docker-compose (e.g.
# services started manually with `uvicorn`/`python worker/main.py`).
# If you're using `docker compose up`, you don't need this file at all -
# the `gridforge-exec-image` service builds the sandbox image for you.

.PHONY: setup up down logs clean

# Build the sandbox image the worker spawns per task. Required once
# before the worker can run anything, and again whenever worker/Dockerfile
# changes.
setup:
	docker build -t gridforge-exec:latest ./worker

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

clean:
	docker compose down -v
	docker image rm gridforge-exec:latest || true
