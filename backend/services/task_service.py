import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import logging
import os
import shutil

from backend.api.models import Task, TaskCreate, TaskUpdate, TaskStatus
from backend.core.config import settings

logger = logging.getLogger(__name__)

_db_path = settings.DB_PATH
_tasks = {}

def _load_db():
    """Loads tasks from the JSON file into memory with file locking."""
    global _tasks
    if not _db_path.exists():
        _tasks = {}
        logger.warning("Tasks DB file not found. Starting with an empty database.")
        return
    
    # Create a backup
    if _db_path.stat().st_size > 0:
        try:
            shutil.copyfile(_db_path, _db_path.with_suffix('.json.bak'))
            logger.info(f"Created backup of DB at {_db_path.with_suffix('.json.bak')}")
        except Exception as e:
            logger.error(f"Could not create backup of DB: {e}")

    try:
        with _db_path.open("r+") as f:
            try:
                # Check if file is empty
                f.seek(0, os.SEEK_END)
                if f.tell() == 0:
                    _tasks = {}
                    logger.warning("Tasks DB file is empty. Starting fresh.")
                    return

                f.seek(0)
                data = json.load(f)
                _tasks = {task_id: Task(**task_data) for task_id, task_data in data.items()}
                logger.info(f"Successfully loaded {_tasks.__len__()} tasks from DB.")
            except json.JSONDecodeError:
                logger.error("Failed to decode tasks DB. Check backup file. Starting fresh.")
                _tasks = {}
            except Exception as e:
                logger.exception(f"An unexpected error occurred during DB load: {e}")
                _tasks = {}
    except IOError as e:
        logger.error(f"Error loading tasks DB: {e}")
        _tasks = {}
    except Exception as e:
        logger.exception(f"A critical error occurred trying to open the DB file: {e}")
        _tasks = {}


def _save_db():
    """Saves the current in-memory tasks to the JSON file with file locking."""
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = _db_path.with_suffix('.json.tmp')
    try:
        with temp_path.open("w") as f:
            json.dump({task_id: task.model_dump(mode='json') for task_id, task in _tasks.items()}, f, indent=4)
        
        # Atomic rename
        os.replace(temp_path, _db_path)
        logger.info(f"Successfully saved {_tasks.__len__()} tasks to DB.")
    except IOError as e:
        logger.error(f"Error saving tasks DB: {e}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred during DB save: {e}")


# Load the DB on startup
_load_db()

def create_task(task_id: str, filename: str) -> Task:
    """Creates a new task and saves it."""
    if task_id in _tasks:
        logger.warning(f"Task with ID {task_id} already exists. Overwriting is not allowed.")
        raise ValueError("Task ID already exists.")
        
    new_task = Task(id=task_id, filename=filename)
    _tasks[new_task.id] = new_task
    _save_db()
    logger.info(f"Created task {new_task.id} for file {filename}")
    return new_task

def get_task(task_id: str) -> Optional[Task]:
    """Retrieves a single task by its ID."""
    return _tasks.get(task_id)

def get_all_tasks() -> List[Task]:
    """Retrieves all tasks."""
    return sorted(list(_tasks.values()), key=lambda t: t.created_at, reverse=True)

def update_task(task_id: str, task_update: TaskUpdate) -> Optional[Task]:
    """Updates a task's status and details."""
    task = _tasks.get(task_id)
    if not task:
        logger.warning(f"Attempted to update non-existent task {task_id}")
        return None

    update_data = task_update.model_dump(exclude_unset=True)
    
    # Log the update attempt
    logger.info(f"Updating task {task_id} with data: {update_data}")

    if "status" in update_data:
        task.status = update_data["status"]
        if task.status == TaskStatus.RUNNING and not task.started_at:
            task.started_at = datetime.utcnow()
        elif task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            if not task.completed_at: # Only set completion time once
                task.completed_at = datetime.utcnow()
                if task.started_at:
                    task.execution_time = (task.completed_at - task.started_at).total_seconds()

    if "logs" in update_data:
        # Append logs instead of replacing
        if task.logs:
            task.logs += "\n" + update_data["logs"]
        else:
            task.logs = update_data["logs"]
    
    if "exit_code" in update_data:
        task.exit_code = update_data["exit_code"]

    _tasks[task_id] = task
    _save_db()
    logger.info(f"Successfully updated task {task_id}. New status: {task.status}")
    return task

def delete_task(task_id: str) -> bool:
    """Deletes a task record and its associated upload directory."""
    logger.info(f"Attempting to delete task {task_id}")
    if task_id in _tasks:
        del _tasks[task_id]
        _save_db()
        logger.info(f"Removed task {task_id} from DB.")
        
        task_dir = settings.UPLOADS_DIR / task_id
        if task_dir.exists():
            try:
                shutil.rmtree(task_dir)
                logger.info(f"Removed task directory {task_dir}")
            except OSError as e:
                logger.error(f"Error removing directory {task_dir}: {e}")
                return False # Deletion was not fully successful
        return True
    else:
        logger.warning(f"Attempted to delete non-existent task {task_id}")
        return False
