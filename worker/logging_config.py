import logging
import sys

def setup_logging():
    """Sets up structured logging for the worker - stdout only.

    Used to also write a local RotatingFileHandler to worker.log, but
    that's exactly the file that ended up committed to git in an earlier
    cleanup pass (logs shouldn't be version-controlled, and a stray local
    file sitting in the working tree risks it happening again). Container
    stdout is already captured by Docker's own log driver - see
    docker-compose.yml's `x-logging`/`logging:` config for backend/worker/
    redis in docker-compose.prod.yml - so a second copy on disk here was
    redundant even before that.
    """
    log_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(log_formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(stream_handler)

    # Quieter logging for libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("docker").setLevel(logging.INFO)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.INFO)
    
    logging.info("--- Worker Logging Initialized ---")
