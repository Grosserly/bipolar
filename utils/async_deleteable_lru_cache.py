"""  here be dragons  """

from collections import OrderedDict
from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar

AsyncCallableReturnType = TypeVar("AsyncCallableReturnType")
AsyncCallable = Callable[[Any], Coroutine[Any, Any, AsyncCallableReturnType]]


def async_deleteable_lru_cache(maxsize: int) -> AsyncCallable:
    def decorator_adlc(func: AsyncCallable) -> AsyncCallable:
        @wraps(func)
        class AsyncDeleteableLRUCache(OrderedDict):  # OrderedDict[tuple, AsyncCallableReturnType]
            def __init__(self, func: AsyncCallable, maxsize: int):
                self.func = func
                self.maxsize = maxsize

            async def __call__(self, *args) -> AsyncCallableReturnType:
                if args in self:
                    value = self[args]
                    self.move_to_end(args)
                    return value
                value = await self.func(*args)
                if len(self) >= self.maxsize:
                    self.popitem(False)
                self[args] = value
                return value

            def delete(self, *args) -> None:
                if args in self:
                    del self[args]

        return AsyncDeleteableLRUCache(func, maxsize)

    return decorator_adlc
