import redis.asyncio as aioredis
from app.config import settings

_redis: aioredis.Redis | None = None

def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis

async def set_vehicle_status(factory_id: str, plate: str, status: str) -> None:
    r = get_redis()
    await r.hset(f"factory:{factory_id}:vehicles", plate, status)

async def get_all_vehicle_statuses(factory_id: str) -> dict:
    r = get_redis()
    return await r.hgetall(f"factory:{factory_id}:vehicles")
