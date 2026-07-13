import requests
import logging
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)

def update_task_status(
    task_id: str,
    status: str,
    logs: Optional[str] = None,
    exit_code: Optional[int] = None,
    execution_time: Optional[float] = None,
):
    """Updates the task status via the backend API."""
    url = f"{settings.API_BASE_URL}/task/{task_id}/update"
    payload = {
        "status": status,
    }
    # Only include these fields if they are not None, to avoid overwriting with null.
    if logs is not None:
        payload["logs"] = logs
    if exit_code is not None:
        payload["exit_code"] = exit_code
    if execution_time is not None:
        payload["execution_time"] = execution_time

    logger.info(f"Attempting to update task {task_id} with payload: {payload}")

    try:
        response = requests.post(
            url,
            json=payload,
            headers={"X-Worker-Key": settings.WORKER_API_KEY},
            timeout=15,
        )
        response.raise_for_status()
        logger.info(f"Successfully updated task {task_id} to status {status}")
        return response.json()
    except requests.exceptions.Timeout:
        logger.error(f"API call to update task {task_id} timed out.")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.error(f"API call failed due to connection error for task {task_id}: {e}")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"API call failed with HTTP error for task {task_id}: {e.response.status_code} - {e.response.text}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"A critical API call error occurred while updating task {task_id}: {e}")
        return None
