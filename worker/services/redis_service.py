import redis
import logging
from config import settings

logger = logging.getLogger(__name__)

_redis_client = None

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
        # Attempt to reconnect
        global _redis_client
        _redis_client = None
        return None
    except Exception as e:
        logger.exception(f"An error occurred while getting task from queue: {e}")
        return None
