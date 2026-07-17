import docker
import time
import logging
from docker.errors import APIError, ImageNotFound, ContainerError, DockerException
from config import settings

logger = logging.getLogger(__name__)

def run_in_container(workspace_path: str):
    """
    Runs the user's project inside a secured Docker container.
    """
    logs = ""
    exit_code = -1
    execution_time = 0.0
    container = None

    # Split off client setup and the image check as their own steps, each
    # with its own early return: neither happens "inside" a container, so
    # there's nothing for the finally block below to retrieve logs from -
    # without this, a failure here left `logs` empty and the user got
    # exit_code=-1 with zero indication of what actually went wrong.
    try:
        logger.info("Initializing Docker client from environment.")
        client = docker.from_env(timeout=60)
        logger.info("Docker client initialized.")
    except DockerException as e:
        logger.error(f"Could not connect to the Docker daemon: {e}", exc_info=True)
        return (
            "[Worker Error] Docker is unavailable - could not connect to the "
            "Docker daemon. This is a worker configuration problem, not an "
            "issue with your project.",
            -1,
            0.0,
        )

    try:
        logger.info(f"Checking for Docker image: {settings.DOCKER_IMAGE}")
        client.images.get(settings.DOCKER_IMAGE)
        logger.info(f"Docker image '{settings.DOCKER_IMAGE}' found.")
    except ImageNotFound:
        logger.error(f"Execution image '{settings.DOCKER_IMAGE}' not found. Please build it first using 'docker build -t {settings.DOCKER_IMAGE} worker/'.")
        return (
            f"[Worker Error] Sandbox image '{settings.DOCKER_IMAGE}' is not "
            f"built on this worker. This is a worker configuration problem, "
            f"not an issue with your project.",
            -1,
            0.0,
        )
    except APIError as e:
        logger.error(f"Docker API error while checking for the sandbox image: {e}", exc_info=True)
        return (
            f"[Worker Error] Docker is unavailable - could not check for the "
            f"sandbox image ({e}).",
            -1,
            0.0,
        )

    try:
        command = [
            "/bin/sh",
            "-c",
            "echo '--- Installing dependencies ---' && if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; else echo 'No requirements.txt found.'; fi && echo '--- Executing main.py ---' && python main.py"
        ]
        logger.info(f"Container command: {' '.join(command)}")

        start_time = time.time()
        
        logger.info(f"Running container with workspace mounted from {workspace_path}")
        container = client.containers.run(
            image=settings.DOCKER_IMAGE,
            command=command,
            volumes={
                workspace_path: {'bind': '/workspace', 'mode': 'ro'} # Read-only mount for security
            },
            working_dir='/workspace',
            detach=True,
            mem_limit=settings.DOCKER_MEM_LIMIT,
            nano_cpus=int(settings.DOCKER_CPU_LIMIT * 1e9),
            network_disabled=True,
            pids_limit=100,
            user='appuser', # Run as non-root user
            log_config={'type': 'json-file', 'config': {'max-size': '1m'}}, # Prevent log spam
        )
        logger.info(f"Container {container.id} started. Waiting for completion (timeout: {settings.DOCKER_TIMEOUT}s).")

        result = container.wait(timeout=settings.DOCKER_TIMEOUT)
        execution_time = time.time() - start_time
        exit_code = result.get('StatusCode', -1)
        logger.info(f"Container {container.id} finished with exit code {exit_code} in {execution_time:.2f} seconds.")

    except ContainerError as e:
        execution_time = time.time() - start_time if 'start_time' in locals() else 0
        logger.warning(f"Container command failed for {container.id if container else 'unknown'}: {e}")
        exit_code = e.exit_status
    except APIError as e:
        execution_time = time.time() - start_time if 'start_time' in locals() else 0
        logger.error(f"Docker API Error: {e}", exc_info=True)
        exit_code = -1
        # container is still None here if client.containers.run() itself
        # raised (e.g. invalid mount, resource limits rejected by the
        # daemon) - same silent-empty-logs gap as the client-init/image
        # checks above, just one step later. If a container DID get
        # created and this happened during .wait() instead, it's non-None
        # and the finally block below retrieves its real logs as usual.
        if container is None:
            logs = f"[Worker Error] Failed to start the sandbox container: {e}"
    except Exception as e:
        execution_time = time.time() - start_time if 'start_time' in locals() else 0
        logger.error(f"An unexpected error occurred with Docker: {e}", exc_info=True)
        exit_code = -1
        if container is None:
            logs = f"[Worker Error] Failed to start the sandbox container: {e}"
    finally:
        if container:
            try:
                logs = container.logs(stdout=True, stderr=True).decode('utf-8', errors='ignore')
                logger.info(f"Retrieved logs from container {container.id}.")
            except APIError as e:
                logger.error(f"Failed to retrieve logs from container {container.id}: {e}")
                logs += "\n[Worker Error: Failed to retrieve container logs]"

            try:
                container.remove(force=True)
                logger.info(f"Cleaned up container {container.id}.")
            except APIError as e:
                logger.error(f"Error cleaning up container {container.id}: {e}")
        
        logger.info(f"run_in_container returning: exit_code={exit_code}, execution_time={execution_time:.2f}s")
        return logs, exit_code, execution_time
