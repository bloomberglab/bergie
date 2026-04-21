# app/db/redis.py

import redis
from app.core.config import settings
from app.core.logging import logger


# Single Redis client instance shared across the app
redis_client = redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,   # return strings, not bytes
    socket_connect_timeout=5,
    socket_timeout=5,
)


def check_redis_connection() -> bool:
    """Health check — returns True if Redis is reachable."""
    try:
        redis_client.ping()
        return True
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        return False