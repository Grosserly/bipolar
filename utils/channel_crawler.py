from typing import Callable
from discord import Message
from discord.iterators import _FilteredAsyncIterator

import inspect


class ChannelCrawler:
    def __init__(self, history: _FilteredAsyncIterator, action: Callable[[Message], bool]):
        self.num_collected = 0
        self.running = True
        self._history = history
        self._action = self._ensure_async(action)


    async def crawl(self) -> None:
        """
        Iterate over up to [limit] messages in the channel in
        reverse-chronological order.
        """
        async for message in self._history:
            if not self.running:
                break

            if await self._action(message):
                self.num_collected += 1

        self.running = False


    def stop(self) -> None:
        self.running = False


    def _ensure_async(func: Callable) -> Callable:
        """ Wrap a function in a coroutine. """
        if inspect.iscoroutinefunction(func):
            return func

        async def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper
