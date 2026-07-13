import logging
import uuid
import shutil
import os
from fastapi import APIRouter, UploadFile, File, HTTPException

from backend.api.models import Task, TaskCreate, TaskUpdate
from backend.services import task_service, redis_service
from backend.core.config import settings
# from backend.core.security import secure_filename # Replaced with standard library
import re

router = APIRouter()
logger = logging.getLogger(__name__)

def secure_filename(filename: str) -> str:
    """A basic version of Werkzeug's secure_filename."""
    _windows_device_files = (
        "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5",
        "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4",
        "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
    )
    filename = re.sub(r'[\s]+', '_', filename)
    filename = re.sub(r'[^a-zA-Z0-9_.-]', '', filename).strip('._')
    if os.name == "nt" and filename.split(".")[0].upper() in _windows_device_files:
        filename = "_" + filename
    return filename


@router.post("/submit-project", response_model=Task)
def submit_project(file: UploadFile = File(...)):
    """
    Accepts a ZIP file upload, stores it, and creates a task.
    """
    logger.info("Received request to /submit-project")
    # 1. File Validation
    if not file.filename:
        logger.error("File submission without a filename.")
        raise HTTPException(status_code=400, detail="No filename provided.")
    if not file.filename.endswith('.zip'):
        logger.error(f"Invalid file type received: {file.filename}")
        raise HTTPException(status_code=400, detail="Invalid file type. Only .zip files are accepted.")

    safe_filename = secure_filename(file.filename)
    logger.info(f"Sanitized filename: {safe_filename}")
    
    # 2. Create Task and Storage Directory
    task_id = str(uuid.uuid4()) # Generate a secure, random task ID
    logger.info(f"Generated new task ID: {task_id}")
    try:
        task = task_service.create_task(task_id=task_id, filename=safe_filename)
        if not task:
            logger.error("Task service failed to create a task record.")
            raise HTTPException(status_code=500, detail="Failed to create task record.")
        logger.info(f"Task record created in DB for task {task.id}")
    except Exception as e:
        logger.exception(f"Exception during task creation for {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during task creation.")

    
    task_dir = settings.UPLOADS_DIR / task.id
    task_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Upload directory created: {task_dir}")
    
    zip_path = task_dir / "project.zip"

    # 3. Store ZIP file
    try:
        logger.info(f"Attempting to save uploaded file to {zip_path}")
        with zip_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"Successfully stored uploaded file for task {task.id} at {zip_path}")
    except IOError as e:
        logger.error(f"Failed to write uploaded file for task {task.id}: {e}")
        # Attempt to clean up
        task_service.delete_task(task.id)
        raise HTTPException(status_code=500, detail="Failed to store uploaded file.")
    finally:
        file.file.close()

    # 4. Queue Task in Redis
    try:
        redis_service.queue_task(task.id)
        logger.info(f"Successfully queued task {task.id} in Redis.")
    except Exception as e:
        logger.exception(f"Failed to queue task {task.id} in Redis: {e}")
        # Attempt to clean up
        task_service.delete_task(task.id)
        if zip_path.exists():
            os.remove(zip_path)
        raise HTTPException(status_code=500, detail="Failed to queue task for processing.")
    
    logger.info(f"Successfully processed submission for task {task.id}. Returning response.")
    return task

@router.get("/task/{task_id}", response_model=Task)
def get_task_status(task_id: str):
    """
    Returns the status and details of a specific task.
    """
    task = task_service.get_task(task_id)
    if not task:
        logger.warning(f"Task {task_id} not found.")
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.get("/results", response_model=list[Task])
def get_all_tasks():
    """
    Returns all tasks, sorted by creation date.
    """
    return task_service.get_all_tasks()

@router.post("/task/{task_id}/update", response_model=Task)
def update_task_status(task_id: str, task_update: TaskUpdate):
    """
    Endpoint for the worker to update task status and results.
    """
    logger.info(f"Received update for task {task_id} with status {task_update.status}")
    task = task_service.update_task(task_id, task_update)
    if not task:
        logger.warning(f"Worker failed to update non-existent task {task_id}")
        raise HTTPException(status_code=404, detail="Task not found")
    logger.info(f"Successfully updated task {task_id}")
    return task
