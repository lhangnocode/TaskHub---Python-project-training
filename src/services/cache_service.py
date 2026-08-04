import json
import logging
import uuid
from typing import Any

from src.config import settings
from src.redis_client import get_redis_client

logger = logging.getLogger(__name__)


def build_project_tasks_cache_key(
    project_id: uuid.UUID,
    status: str | None,
    priority: str | None,
    assignee_id: uuid.UUID | None,
    page: int,
    limit: int,
) -> str:
    s_val = status or "all"
    p_val = priority or "all"
    a_val = str(assignee_id) if assignee_id else "all"
    return f"cache:project:{project_id}:tasks:s={s_val}:p={p_val}:a={a_val}:pg={page}:lim={limit}"


async def get_cached_project_tasks(cache_key: str) -> dict[str, Any] | None:
    try:
        redis_conn = await get_redis_client()
        data = await redis_conn.get(cache_key)
        if data:
            logger.debug("Redis cache HIT for key: %s", cache_key)
            return json.loads(data)  # type: ignore[no-any-return]
    except Exception as exc:
        logger.warning("Redis read error for key %s: %s", cache_key, exc)
    return None


async def set_cached_project_tasks(
    cache_key: str, data: dict[str, Any], ttl: int = settings.REDIS_CACHE_TTL_SECONDS
) -> None:
    try:
        redis_conn = await get_redis_client()
        await redis_conn.setex(cache_key, ttl, json.dumps(data, default=str))
        logger.debug("Redis cache SET for key: %s (TTL: %ds)", cache_key, ttl)
    except Exception as exc:
        logger.warning("Redis write error for key %s: %s", cache_key, exc)


async def invalidate_project_tasks_cache(project_id: uuid.UUID) -> None:
    pattern = f"cache:project:{project_id}:tasks:*"
    try:
        redis_conn = await get_redis_client()
        keys = []
        async for key in redis_conn.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            await redis_conn.delete(*keys)
            logger.info(
                "Invalidated %d Redis cache keys for project %s", len(keys), project_id
            )
    except Exception as exc:
        logger.warning("Redis invalidation error for project %s: %s", project_id, exc)
