import asyncio
from collections import OrderedDict
import functools
import logging
import traceback
from collections.abc import AsyncIterator, Callable, Coroutine
from enum import Enum
from typing import Any, cast

import discord
from discord.ext import commands

from parrot import config
from parrot.utils import regex
from parrot.utils.types import AnyUser


class HistoryCrawler:
	def __init__(
		self,
		histories: AsyncIterator | list[AsyncIterator],
		action: Callable[[discord.Message], bool],
		limit: int = 100_000,
		filter: Callable[[discord.Message], bool] = lambda _: True,
	):
		self.num_collected = 0
		self.running = True
		self._action = action
		self._limit = limit
		self._filter = filter
		if isinstance(histories, list):
			self._histories = histories
		else:
			self._histories = [histories]

	async def crawl(self) -> None:
		"""
		Iterate over up to [limit] messages in the channel in
		reverse-chronological order.
		"""
		for history in self._histories:
			async for message in history:
				if not self.running:
					break
				if not self._filter(message):
					continue
				if self._action(message):
					self.num_collected += 1
				if self.num_collected >= self._limit:
					break
		self.running = False

	def stop(self) -> None:
		self.running = False


class LastUpdatedOrderedDict[K, V](OrderedDict):
	"""Store items in the order the keys were last added"""

	def __setitem__(self, key: K, value: V):
		super().__setitem__(key, value)
		self.move_to_end(key)


class ParrotEmbed(discord.Embed):
	"""
	Concepts stolen from crimsoBOT
	MIT License
	Copyright (c) 2019 crimso, williammck
	https://github.com/crimsobot/crimsoBOT/285ebfd/master/crimsobot/utils/tools.py#L37-L123
	"""

	class Color(Enum):
		DEFAULT = 0xA755B5  # Pale purple
		RED = 0xB71C1C  # Deep, muted red
		ORANGE = 0xF4511E  # Deep orange. Reserved for BIG trouble.
		GREEN = 0x43A047  # Darkish muted green
		GRAY = 0x9E9E9E  # Dead gray

	def __init__(
		self, color_name: Color = Color.DEFAULT, *args: ..., **kwargs: ...
	):
		kwargs["color"] = kwargs.get("color", color_name.value)
		super().__init__(*args, **kwargs)


def cast_not_none[T](arg: T | None) -> T:
	return cast(T, arg)


def error2traceback(error: Exception) -> str:
	return "\n".join(
		traceback.format_exception(None, error, error.__traceback__)
	)


def executor_function[**P, Ret](
	sync_function: Callable[P, Ret],
) -> Callable[P, Coroutine[Any, Any, Ret]]:
	@functools.wraps(sync_function)
	async def decorated(*args: P.args, **kwargs: P.kwargs) -> Ret:
		loop = asyncio.get_event_loop()
		function_curried = functools.partial(sync_function, *args, **kwargs)
		return await loop.run_in_executor(None, function_curried)

	return decorated


def discord_caps(text: str) -> str:
	"""
	Capitalize a string in a way that remains friendly to URLs, emojis, and
	mentions.
	Credit to https://github.com/redgoldlace
	"""
	words = text.replace("*", "").split(" ")
	for i, word in enumerate(words):
		if regex.do_not_capitalize.match(word) is None:
			words[i] = word.upper()
	return " ".join(words)


def find_text(message: discord.Message) -> str:
	"""
	Search for text within a message.
	Return an empty string if no text is found.
	"""
	text = []
	if len(message.content) > 0 and not message.content.startswith(
		config.command_prefix
	):
		text.append(message.content)
	for embed in message.embeds:
		if isinstance(embed.description, str) and len(embed.description) > 0:
			text.append(embed.description)
	return " ".join(text)


def tag(user: AnyUser) -> str:
	if user.discriminator != "0":
		return f"@{user.name}#{user.discriminator}"
	return f"@{user.name}"


def trace_format_command_origin(ctx: commands.Context) -> str:
	result = ""
	if ctx.guild is not None:
		result += f"{ctx.guild.name} - "
	if isinstance(ctx.channel, discord.TextChannel):
		result += f"#{ctx.channel.name} - "
	result += tag(ctx.author)
	return result


# TODO: type annotate this finelier without Pylance exploding
def trace[**P, Ret](
	fn: Callable,  # Callable[P, Awaitable[Ret]],
) -> Callable:  # Callable[P, Awaitable[Ret]]:
	@functools.wraps(fn)
	async def decorated(*args: P.args, **kwargs: P.kwargs) -> Ret:
		if len(args) >= 2 and isinstance(args[0], commands.Cog):
			ctx = cast(commands.Context, args[1])
			logging.info(
				f"{trace_format_command_origin(ctx)}: "
				f"{args[0].__cog_name__}.{fn.__name__} {kwargs}"
			)
		else:
			logging.info(fn.__name__, *args, **kwargs)
		return await fn(*args, **kwargs)

	return decorated
