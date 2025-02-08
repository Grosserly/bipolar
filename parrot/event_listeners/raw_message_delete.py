import logging

import discord
from discord.ext import commands

from parrot.bot import Parrot


class RawMessageDeleteEventHandler(commands.Cog):
	def __init__(self, bot: Parrot):
		self.bot = bot

	@commands.Cog.listener()
	async def on_raw_message_delete(
		self, event: discord.RawMessageDeleteEvent
	) -> None:
		"""
		Update the database when a message is deleted.
		Must use the raw event because the regular version doesn't work for
		messages that don't happen to be in its cache.
		"""
		deleted = self.bot.crud.message.delete(event.message_id)
		if deleted is None:
			return
		# Invalidate cached model
		try:
			del self.bot.markov_models.cache[
				(deleted.author_id, deleted.guild_id)
			]
		except KeyError:
			pass
		logging.info(
			f"Forgot message with ID {event.message_id} because it was deleted "
			"from Discord."
		)


async def setup(bot: Parrot) -> None:
	await bot.add_cog(RawMessageDeleteEventHandler(bot))
