import logging
import shutil
from datetime import datetime
from typing import List, Optional

from sqlalchemy.exc import IntegrityError

from backend.api.models import Task, TaskStatus, TaskUpdate
from backend.core.config import settings
from backend.db.database import SessionLocal, init_db
from backend.db.models import TaskORM

logger = logging.getLogger(__name__)

# Creates the tasks table if it doesn't exist yet. Idempotent, so running it
# on every import (i.e. every process start) is safe - see
# backend/db/init_db.py for the equivalent explicit/standalone step.
init_db()


def create_task(task_id: str, filename: str) -> Task:
    """Creates a new task and saves it."""
    new_task = TaskORM(
        id=task_id,
        filename=filename,
        status=TaskStatus.QUEUED.value,
        created_at=datetime.utcnow(),
    )
    with SessionLocal() as session:
        session.add(new_task)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            logger.warning(f"Task with ID {task_id} already exists. Overwriting is not allowed.")
            raise ValueError("Task ID already exists.")
        session.refresh(new_task)
        logger.info(f"Created task {new_task.id} for file {filename}")
        return Task.model_validate(new_task)


def get_task(task_id: str) -> Optional[Task]:
    """Retrieves a single task by its ID."""
    with SessionLocal() as session:
        task = session.get(TaskORM, task_id)
        return Task.model_validate(task) if task else None


def get_all_tasks() -> List[Task]:
    """Retrieves all tasks, newest first."""
    with SessionLocal() as session:
        tasks = session.query(TaskORM).order_by(TaskORM.created_at.desc()).all()
        return [Task.model_validate(t) for t in tasks]


def update_task(task_id: str, task_update: TaskUpdate) -> Optional[Task]:
    """Updates a task's status and details."""
    update_data = task_update.model_dump(exclude_unset=True)
    logger.info(f"Updating task {task_id} with data: {update_data}")

    with SessionLocal() as session:
        # SQLite serializes writers at the file level, so this read-then-
        # write within one session/transaction is race-free against other
        # writers - a concurrent update_task() for the same row simply
        # blocks (up to the busy_timeout configured in database.py) until
        # this transaction commits, rather than interleaving.
        task = session.get(TaskORM, task_id)
        if not task:
            logger.warning(f"Attempted to update non-existent task {task_id}")
            return None

        if "status" in update_data:
            task.status = update_data["status"]
            if task.status == TaskStatus.RUNNING.value and not task.started_at:
                task.started_at = datetime.utcnow()
            elif task.status in (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value):
                if not task.completed_at:  # Only set completion time once
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

        session.commit()
        session.refresh(task)
        logger.info(f"Successfully updated task {task_id}. New status: {task.status}")
        return Task.model_validate(task)


def delete_task(task_id: str) -> bool:
    """Deletes a task record and its associated upload directory."""
    logger.info(f"Attempting to delete task {task_id}")
    with SessionLocal() as session:
        task = session.get(TaskORM, task_id)
        if not task:
            logger.warning(f"Attempted to delete non-existent task {task_id}")
            return False

        session.delete(task)
        session.commit()
        logger.info(f"Removed task {task_id} from DB.")

    task_dir = settings.UPLOADS_DIR / task_id
    if task_dir.exists():
        try:
            shutil.rmtree(task_dir)
            logger.info(f"Removed task directory {task_dir}")
        except OSError as e:
            logger.error(f"Error removing directory {task_dir}: {e}")
            return False  # Deletion was not fully successful
    return True
