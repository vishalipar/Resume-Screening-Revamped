import logging
from concurrent.futures import ThreadPoolExecutor
from django.db import close_old_connections

logger = logging.getLogger(__name__)

# ThreadPoolExecutor to run tasks asynchronously in the background
# We set max_workers=3 to allow parallel email/NLP processing
executor = ThreadPoolExecutor(max_workers=3)

def _execute_task(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except Exception as e:
        logger.exception("Error executing background task: %s", str(e))
    finally:
        # Clean up database connections for the thread
        close_old_connections()

def run_in_background(func, *args, **kwargs):
    """Executes a function asynchronously in a background thread."""
    executor.submit(_execute_task, func, *args, **kwargs)
