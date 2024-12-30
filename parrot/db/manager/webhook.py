from typing import TYPE_CHECKING

import discord
from discord import Forbidden, HTTPException, NotFound

from parrot.utils import cast_not_none


if TYPE_CHECKING:
	from parrot.bot import Parrot

class WebhookManager:
	def __init__(self, bot: "Parrot"):
		self.bot = bot

	async def fetch(
		self, channel: discord.TextChannel
	) -> discord.Webhook | None:
		# See if Parrot owns a webhook for this channel.
		webhook_id = self.bot.crud.channel.get_webhook_id(channel)
		if webhook_id is not None:
			try:
				return await self.bot.fetch_webhook(webhook_id)
			except NotFound:
				# Saved webhook ID is invalid; make a new one
				pass

		# Parrot does not have a webhook for this channel, so create one.
		try:
			parrots_avatar = await cast_not_none(
				self.bot.user
			).display_avatar.read()
			webhook = await channel.create_webhook(
				name=f"Parrot in #{channel.name}",
				avatar=parrots_avatar,
				reason="Automatically created by Parrot",
			)
			self.bot.crud.channel.set_webhook_id(channel, webhook)
			return webhook
		except (Forbidden, HTTPException, AttributeError):
			# - Forbidden: Parrot lacks permission to make webhooks here.
			# - AttributeError: Cannot make a webhook in this type of channel, like
			#   a DMChannel.
			# - HTTPException: 400 Bad Request; there is already the maximum number
			#   of webhooks allowed in this channel (10).
			return None
