import time
import logging
import threading
from prisma import Prisma

logger = logging.getLogger(__name__)

_db = Prisma()
_lock = threading.Lock()
_MAX_RETRIES = 3
_RETRY_BACKOFF = 0.5


def get_db():
    """
    Thread-safe singleton access to the Prisma client.
    Uses a lock to prevent concurrent connect() calls (TOCTOU race).
    Retries with exponential backoff on connection failure.
    """
    if _db.is_connected():
        return _db

    with _lock:
        if _db.is_connected():
            return _db

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                _db.connect()
                logger.info("[DB] Prisma client connected.")
                return _db
            except Exception as e:
                wait = _RETRY_BACKOFF * (2 ** (attempt - 1))
                logger.warning(f"[DB] Connection attempt {attempt}/{_MAX_RETRIES} failed: {e}. Retrying in {wait}s...")
                if attempt == _MAX_RETRIES:
                    logger.error(f"[DB] All {_MAX_RETRIES} connection attempts failed.")
                    raise
                time.sleep(wait)

    return _db


def disconnect_db():
    """Gracefully disconnect the Prisma client."""
    with _lock:
        if _db.is_connected():
            try:
                _db.disconnect()
                logger.info("[DB] Prisma client disconnected.")
            except Exception as e:
                logger.warning(f"[DB] Error during disconnect: {e}")
