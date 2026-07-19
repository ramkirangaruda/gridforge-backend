import logging
import sys

def setup_logging():
    """stdout only, deliberately - see worker/logging_config.py's
    docstring for why (also stdout-only, for the same reason)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
