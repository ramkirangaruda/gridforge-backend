import redis
import redis.asyncio as aredis
import json
import logging
from backend.core.config import settings

logger = logging.getLogger(__name__)

_redis_client = None
_async_redis_client = None

def _update_channel(owner: str) -> str:
    return f"gridforge_updates:{owner}"

def get_redis_client():
    """
    Initializes and returns a Redis client.
    Includes a PING check to verify the connection.
    """
    global _redis_client
    if _redis_client is None:
        logger.info(f"Connecting to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        try:
            _redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=5 # Add a timeout
            )
            # Check the connection
            _redis_client.ping()
            logger.info("Successfully connected to Redis.")
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            _redis_client = None # Reset on failure
            raise
    return _redis_client

def queue_task(task_id: str):
    """Pushes a task ID into the Redis queue."""
    try:
        client = get_redis_client()
        if client:
            client.lpush(settings.REDIS_QUEUE_NAME, task_id)
            logger.info(f"Pushed task {task_id} to queue '{settings.REDIS_QUEUE_NAME}'")
        else:
            logger.error("Cannot queue task, Redis client is not available.")
            raise ConnectionError("Redis client not available.")
    except Exception as e:
        logger.exception(f"An error occurred while queueing task {task_id}: {e}")
        raise

def get_task_from_queue(timeout: int = 0) -> str | None:
    """
    Retrieves a task ID from the Redis queue.
    Uses blocking pop with an optional timeout.
    """
    try:
        client = get_redis_client()
        if client:
            logger.debug(f"Worker waiting for task from queue '{settings.REDIS_QUEUE_NAME}'...")
            # Use blocking pop to wait for a task
            result = client.brpop(settings.REDIS_QUEUE_NAME, timeout=timeout)
            if result:
                _, task_id = result
                logger.info(f"Worker received task {task_id} from queue.")
                return task_id
            else:
                # This will happen if the timeout is reached
                logger.debug("brpop timed out, no task in queue.")
                return None
        else:
            logger.error("Cannot get task from queue, Redis client is not available.")
            return None
    except redis.exceptions.ConnectionError as e:
        logger.error(f"Redis connection error in worker: {e}")
        return None
    except Exception as e:
        logger.exception(f"An error occurred while getting task from queue: {e}")
        return None

def get_async_redis_client() -> aredis.Redis:
    """Async counterpart of get_redis_client(), used only by the SSE stream
    endpoint - that handler is a long-lived async generator, so it needs a
    client that can await on pubsub messages without blocking the event
    loop (the sync client's blocking calls would stall every other request
    the backend is serving)."""
    global _async_redis_client
    if _async_redis_client is None:
        _async_redis_client = aredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )
    return _async_redis_client

def publish_task_update(owner: str, task_payload: dict):
    """Publishes a task's current state to that task owner's channel. Best-
    effort: if Redis is unreachable, the DB write the caller already did is
    still the source of truth - SSE clients just miss a live update and get
    the current state on their next reconnect/snapshot instead."""
    if not owner:
        return
    try:
        client = get_redis_client()
        client.publish(_update_channel(owner), json.dumps(task_payload))
    except Exception as e:
        logger.error(f"Failed to publish task update for owner {owner}: {e}")

async def subscribe_to_user_updates(owner: str):
    """Returns a PubSub subscribed to one user's update channel."""
    client = get_async_redis_client()
    pubsub = client.pubsub()
    await pubsub.subscribe(_update_channel(owner))
    return pubsub
