import redis.asyncio as aioredis  # included in redis>=4.2
from redis.exceptions import RedisError
from fastapi import HTTPException, status, Request
from app.config import settings

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def check_rate_limit(key: str, limit: int = 10, window_seconds: int = 60) -> bool:
    """Returns True if under limit, raises 429 if exceeded."""
    r = await get_redis()
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds)
    try:
        results = await pipe.execute()
    except (OSError, RedisError):
        return True
    count = results[0]
    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please slow down.",
        )
    return True


async def rate_limit_middleware(request: Request, user_id: str):
    """Apply per-user rate limiting: 10 requests/minute."""
    key = f"rate_limit:{user_id}:{request.url.path}"
    await check_rate_limit(key, limit=10, window_seconds=60)


async def cache_get(key: str) -> str | None:
    r = await get_redis()
    try:
        return await r.get(key)
    except (OSError, RedisError):
        return None


async def cache_set(key: str, value: str, ttl_seconds: int = 300):
    r = await get_redis()
    try:
        await r.setex(key, ttl_seconds, value)
    except (OSError, RedisError):
        return


async def cache_delete(key: str):
    r = await get_redis()
    try:
        await r.delete(key)
    except (OSError, RedisError):
        return
