import logging

import redis.asyncio as redis

from src.config import settings

logger = logging.getLogger(__name__)

redis_client: redis.Redis | None = None


async def get_redis_client() -> redis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True,
        )
    return redis_client


async def close_redis_client() -> None:
    global redis_client
    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None
