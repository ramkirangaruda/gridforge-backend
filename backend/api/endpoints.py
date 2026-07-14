import json
import logging
import uuid
import shutil
import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm

from backend.api.models import Task, TaskUpdate, UserCreate, Token
from backend.services import task_service, redis_service, user_service
from backend.core.config import settings
from backend.core.auth import get_current_user, get_current_user_sse, verify_worker_key, create_access_token
from backend.core.rate_limit import limiter
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


@router.post("/auth/register", status_code=201)
@limiter.limit("5/minute")
def register(request: Request, user: UserCreate):
    """
    Registers a new user. No email verification/roles/etc - just enough
    to demonstrate per-user access control.

    Rate-limited to 5/minute per IP: generous enough that nobody fumbling
    a signup form hits it, tight enough to make scripted registration spam
    (filling the users table, or probing for taken usernames) impractical.
    This is a demo-appropriate number, not a production-tuned one - a
    real deployment facing actual abuse would likely want this lower, plus
    a CAPTCHA or email verification step, neither of which is in scope here.
    """
    try:
        user_service.create_user(user.username, user.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": "User registered successfully."}


@router.post("/auth/login", response_model=Token)
@limiter.limit("5/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Exchanges a username/password for a JWT access token. Send the token
    back as `Authorization: Bearer <token>` on subsequent requests.

    Rate-limited to 5/minute per IP - the main goal is blunting online
    password-guessing against a single account. Per-IP is what's asked
    for here and is enough to stop a naive brute force from one machine,
    but it does NOT stop a distributed attack spreading guesses across
    many IPs at one username; a stricter per-username lockout would be
    the next layer to add if that threat model matters for this deployment.
    """
    if not user_service.authenticate_user(form_data.username, form_data.password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(form_data.username)
    return Token(access_token=access_token)


@router.post("/submit-project", response_model=Task)
def submit_project(file: UploadFile = File(...), current_user: str = Depends(get_current_user)):
    """
    Accepts a ZIP file upload, stores it, and creates a task owned by the
    authenticated user.
    """
    logger.info(f"Received request to /submit-project from user {current_user}")
    # 1. File Validation
    if not file.filename:
        logger.error("File submission without a filename.")
        raise HTTPException(status_code=400, detail="No filename provided.")
    if not file.filename.endswith('.zip'):
        logger.error(f"Invalid file type received: {file.filename}")
        raise HTTPException(status_code=400, detail="Invalid file type. Only .zip files are accepted.")

    # file.size reflects what Starlette actually received - unlike the
    # Content-Length header (already checked earlier by
    # MaxBodySizeMiddleware, see main.py), it can't be spoofed by the
    # client, so this is the authoritative check even though by this point
    # the body has already been read. Checked before creating any task
    # record or writing anything to uploads/, so an oversized upload leaves
    # no partial state behind.
    if file.size is not None and file.size > settings.MAX_UPLOAD_SIZE_BYTES:
        logger.warning(f"Rejected upload from {current_user}: {file.size} bytes exceeds the {settings.MAX_UPLOAD_SIZE_BYTES} byte limit.")
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB.",
        )

    # 1b. Per-user storage quota
    current_usage = task_service.get_user_storage_usage(current_user)
    if file.size is not None and current_usage + file.size > settings.MAX_USER_STORAGE_BYTES:
        logger.warning(
            f"Rejected upload from {current_user}: {current_usage} + {file.size} bytes "
            f"would exceed the {settings.MAX_USER_STORAGE_BYTES} byte per-user quota."
        )
        raise HTTPException(
            status_code=413,
            detail=(
                f"This upload would exceed your storage quota "
                f"({settings.MAX_USER_STORAGE_BYTES // (1024 * 1024)}MB total). "
                f"Delete some previous tasks and try again."
            ),
        )

    safe_filename = secure_filename(file.filename)
    logger.info(f"Sanitized filename: {safe_filename}")

    # 2. Create Task and Storage Directory
    task_id = str(uuid.uuid4()) # Generate a secure, random task ID
    logger.info(f"Generated new task ID: {task_id}")
    try:
        task = task_service.create_task(
            task_id=task_id, filename=safe_filename, owner=current_user, file_size=file.size
        )
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
def get_task_status(task_id: str, current_user: str = Depends(get_current_user)):
    """
    Returns the status and details of a specific task, if it belongs to
    the authenticated user.
    """
    task = task_service.get_task(task_id)
    # Same 404 whether the task doesn't exist or just isn't yours - avoids
    # leaking other users' task IDs via a distinct "403 Forbidden" response.
    if not task or task.owner != current_user:
        logger.warning(f"Task {task_id} not found or not owned by {current_user}.")
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.get("/results", response_model=list[Task])
def get_all_tasks(current_user: str = Depends(get_current_user)):
    """
    Returns the authenticated user's tasks, sorted by creation date.
    """
    return task_service.get_all_tasks(owner=current_user)

@router.post("/task/{task_id}/update", response_model=Task, dependencies=[Depends(verify_worker_key)])
def update_task_status(task_id: str, task_update: TaskUpdate):
    """
    Endpoint for the worker to update task status and results. Authenticated
    via a shared worker API key (X-Worker-Key header), not a user JWT - the
    worker has no user identity of its own.
    """
    logger.info(f"Received update for task {task_id} with status {task_update.status}")
    task = task_service.update_task(task_id, task_update)
    if not task:
        logger.warning(f"Worker failed to update non-existent task {task_id}")
        raise HTTPException(status_code=404, detail="Task not found")
    logger.info(f"Successfully updated task {task_id}")
    redis_service.publish_task_update(task.owner, task.model_dump(mode="json"))
    return task


@router.get("/stream/tasks")
async def stream_tasks(request: Request, current_user: str = Depends(get_current_user_sse)):
    """
    Server-Sent Events stream of the authenticated user's task updates.
    Replaces the frontend's old 2s-polling loop against /results: an
    initial `snapshot` event carries the user's current tasks, then a
    `task_update` event fires each time the worker posts a status change
    for one of their tasks (pushed via Redis pub/sub - see
    update_task_status above and redis_service.publish_task_update).
    """
    async def event_generator():
        tasks = task_service.get_all_tasks(owner=current_user)
        yield f"event: snapshot\ndata: {json.dumps([t.model_dump(mode='json') for t in tasks])}\n\n"

        pubsub = await redis_service.subscribe_to_user_updates(current_user)
        try:
            while True:
                if await request.is_disconnected():
                    logger.info(f"SSE client for {current_user} disconnected.")
                    break
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15)
                if message:
                    yield f"event: task_update\ndata: {message['data']}\n\n"
                else:
                    # No update in the last 15s - send a comment line (not a
                    # real event) purely to keep the connection alive
                    # through intermediary proxies/load balancers that time
                    # out idle HTTP connections.
                    yield ": heartbeat\n\n"
        finally:
            await pubsub.unsubscribe()
            await pubsub.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Disable response buffering if this ever sits behind nginx.
            "X-Accel-Buffering": "no",
        },
    )
