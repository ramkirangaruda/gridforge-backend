import logging
import sys
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Sets up structured logging for the worker."""
    log_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # Console Handler
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(log_formatter)
    
    # File Handler
    file_handler = RotatingFileHandler("worker.log", maxBytes=5*1024*1024, backupCount=2)
    file_handler.setFormatter(log_formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)

    # Quieter logging for libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("docker").setLevel(logging.INFO)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.INFO)
    
    logging.info("--- Worker Logging Initialized ---")
