import docker
import time
import logging
from docker.errors import APIError, ImageNotFound, ContainerError
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
    
    try:
        logger.info("Initializing Docker client from environment.")
        client = docker.from_env(timeout=60)
        logger.info("Docker client initialized.")

        try:
            logger.info(f"Checking for Docker image: {settings.DOCKER_IMAGE}")
            client.images.get(settings.DOCKER_IMAGE)
            logger.info(f"Docker image '{settings.DOCKER_IMAGE}' found.")
        except ImageNotFound:
            logger.error(f"Execution image '{settings.DOCKER_IMAGE}' not found. Please build it first using 'docker build -t {settings.DOCKER_IMAGE} worker/'.")
            raise

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
    except Exception as e:
        execution_time = time.time() - start_time if 'start_time' in locals() else 0
        logger.error(f"An unexpected error occurred with Docker: {e}", exc_info=True)
        exit_code = -1
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
