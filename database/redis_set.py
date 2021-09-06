from typing import Awaitable, Iterator, cast, Union
from aioredis import Redis

# The valid Redis value types
RedisSetValue = Union[bytes, str, int, float]


class RedisSet:
    """ A proxy to a set in a Redis database. """
    def __init__(self, redis: Redis, key: str):
        self.redis = redis
        self.key = key

    async def has(self, element: RedisSetValue) -> bool:
        return await self.redis.sismember(self.key, element)

    async def values(self) -> Iterator[RedisSetValue]:
        return await self.redis.smembers(self.key)

    async def size(self) -> int:
        return await cast(Awaitable[int], self.redis.scard(self.key))

    async def add(self, element: RedisSetValue) -> None:
        await self.redis.sadd(self.key, element)

    async def remove(self, element: RedisSetValue) -> None:
        await self.redis.srem(self.key, element)

    async def clear(self) -> None:
        await self.redis.delete(self.key)
