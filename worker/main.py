import sys
import time
import zipfile
import shutil
import logging

import requests

from config import settings
from docker_runner import run_in_container
from logging_config import setup_logging
from api_client import update_task_status
from services.redis_service import get_task_from_queue, get_redis_client

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)


def verify_worker_key_matches_backend() -> bool:
    """Confirms WORKER_API_KEY is actually accepted by the backend before
    the main loop starts pulling tasks.

    Every /task/{id}/update call needs this key (see verify_worker_key in
    backend/core/auth.py), but api_client.py logs and swallows HTTP
    errors rather than raising - so on its own, a mismatched key
    wouldn't surface as anything louder than a per-call error buried in
    the worker's log file, and only *after* a task has already been
    popped off the (destructive) Redis queue, run for real, and had its
    result thrown away because the backend could never be told about it.
    Checking once here, before any task is ever pulled, avoids wasting
    real compute on a task doomed to have its result discarded.

    Returns True once verified. Returns False (caller should retry) if
    the backend isn't reachable yet - that's expected during startup and
    not treated as fatal. Exits the process immediately on a definitive
    403, since that's a real misconfiguration retrying won't fix.
    """
    url = f"{settings.API_BASE_URL}/worker/ping"
    try:
        response = requests.get(
            url, headers={"X-Worker-Key": settings.WORKER_API_KEY}, timeout=10
        )
    except requests.exceptions.RequestException as e:
        logger.warning(f"Could not reach backend at {url} to verify WORKER_API_KEY yet: {e}")
        return False

    if response.status_code == 200:
        logger.info("WORKER_API_KEY verified against the backend.")
        return True

    if response.status_code == 403:
        logger.critical(
            "WORKER_API_KEY does not match the backend's configured key. "
            "Every task update this worker sends would be silently rejected "
            "until this is fixed, so refusing to start rather than waste "
            "compute on tasks whose results could never be reported. Set "
            "WORKER_API_KEY to the same value in both the backend's and the "
            "worker's environment."
        )
        sys.exit(1)

    logger.warning(f"Unexpected response ({response.status_code}) verifying WORKER_API_KEY against the backend; will retry.")
    return False

def process_task(task_id: str):
    """
    The main task processing logic.
    """
    logger.info(f"Processing task: {task_id}")
    
    try:
        update_task_status(task_id, "running")
    except Exception as e:
        logger.error(f"Failed to update task {task_id} to 'running' status. Aborting. Error: {e}")
        # We can't proceed if we can't even update the status.
        return

    task_workspace = settings.WORKSPACES_DIR / task_id
    zip_path = task_workspace / "project.zip"
    
    # The extraction path is the workspace itself.
    extract_path = task_workspace

    # 1. Safety check and Cleanup
    logger.info(f"Cleaning up workspace for task {task_id} at {extract_path}")
    try:
        # Clean up previous contents except the zip file itself
        for item in extract_path.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            elif item.is_file() and item.name != "project.zip":
                item.unlink()
    except Exception as e:
        error_message = f"Error during workspace cleanup for task {task_id}: {e}"
        logger.error(error_message)
        update_task_status(task_id, "failed", logs=error_message)
        return

    # 2. Unzip the project
    try:
        logger.info(f"Validating and extracting ZIP for task {task_id}")
        if not zip_path.exists():
            raise FileNotFoundError("Project ZIP file not found.")
            
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Secure extraction: reject path traversal, and reject zip
            # bombs by summing each entry's *declared* uncompressed size
            # before extracting anything - a small, highly-compressed zip
            # can still decompress to gigabytes, so the compressed size on
            # disk (already capped by the backend, see MAX_UPLOAD_SIZE_BYTES
            # in api/endpoints.py) tells us nothing about that risk.
            total_uncompressed_size = 0
            for member in zip_ref.infolist():
                if ".." in member.filename or member.filename.startswith('/'):
                    raise ValueError("Malicious ZIP file detected (invalid member).")
                total_uncompressed_size += member.file_size
                if total_uncompressed_size > settings.MAX_UNCOMPRESSED_ZIP_SIZE:
                    raise ValueError(
                        f"ZIP archive's uncompressed size exceeds the "
                        f"{settings.MAX_UNCOMPRESSED_ZIP_SIZE} byte limit "
                        f"(likely a zip bomb)."
                    )
            zip_ref.extractall(extract_path)
        logger.info(f"Successfully extracted project for task {task_id} to {extract_path}")
    except (zipfile.BadZipFile, ValueError, FileNotFoundError) as e:
        error_message = f"Failed to extract zip for task {task_id}: {e}"
        logger.error(error_message)
        update_task_status(task_id, "failed", logs=error_message)
        return
    except Exception as e:
        error_message = f"An unexpected error occurred during ZIP extraction for task {task_id}: {e}"
        logger.exception(error_message)
        update_task_status(task_id, "failed", logs=error_message)
        return

    # 3. Validate project structure
    main_py = extract_path / "main.py"
    if not main_py.is_file():
        error_message = "Error: main.py not found in the root of the ZIP archive."
        logger.error(f"{error_message} for task {task_id}")
        update_task_status(task_id, "failed", logs=error_message)
        return
    logger.info(f"Project structure validated for task {task_id}. main.py found.")

    # 4. Run in Docker
    try:
        logger.info(f"Starting container execution for task {task_id}")
        logs, exit_code, exec_time = run_in_container(str(extract_path))
        status = "completed" if exit_code == 0 else "failed"
        logger.info(f"Container for task {task_id} finished with status '{status}' and exit code {exit_code}.")
        update_task_status(task_id, status, logs=logs, exit_code=exit_code, execution_time=exec_time)
    except Exception as e:
        error_message = f"Worker Error: Could not execute task in container. {e}"
        logger.exception(f"Critical error during Docker execution for task {task_id}")
        update_task_status(task_id, "failed", logs=error_message)
    finally:
        # 5. Cleanup (optional, can be disabled for debugging)
        # shutil.rmtree(extract_path)
        logger.info(f"Finished processing task {task_id}")


def main():
    logger.info("GridForge Worker starting up...")
    
    # Loop to ensure Redis is available before starting the main loop
    while True:
        try:
            get_redis_client() # This will try to connect and ping
            logger.info("Redis connection confirmed. Worker is ready.")
            break
        except Exception as e:
            logger.error(f"Could not connect to Redis on startup. Retrying in 10 seconds... Error: {e}")
            time.sleep(10)

    # Loop to ensure the backend is reachable AND actually accepts this
    # worker's WORKER_API_KEY before pulling any tasks. Exits the process
    # outright on a confirmed key mismatch (see the function docstring);
    # only retries for "backend not reachable yet", which is normal
    # during startup ordering.
    while not verify_worker_key_matches_backend():
        time.sleep(10)

    logger.info(f"Worker waiting for tasks on queue '{settings.REDIS_QUEUE_NAME}'...")
    while True:
        task_id = None
        try:
            # Blocking pop with a timeout of 0 means it will wait indefinitely
            task_id = get_task_from_queue(timeout=0) 
            if task_id:
                process_task(task_id)
        except Exception as e:
            logger.exception(f"An unexpected error occurred in the main worker loop for task '{task_id if task_id else 'unknown'}'")
            if task_id:
                try:
                    # Try to mark the task as failed if a catastrophic error happened
                    update_task_status(task_id, "failed", logs=f"A critical, unexpected error occurred in the worker: {e}")
                except Exception as update_e:
                    logger.error(f"Could not even update the task status to failed after a crash: {update_e}")
            # Wait a moment before continuing to prevent rapid-fire failures on a systemic issue
            time.sleep(10)

if __name__ == "__main__":
    main()
