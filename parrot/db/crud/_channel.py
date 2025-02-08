import discord
import sqlmodel as sm

import parrot.db.models as p
from parrot.utils import cast_not_none
from parrot.utils.types import Permission, Snowflake

from .types import SubCRUD


class CRUDChannel(SubCRUD):
	def set_permission_flag(
		self, channel: discord.TextChannel, permission: Permission, value: bool
	) -> bool:
		"""
		Set the value of a Parrot permission flag for a channel.

		:param channel: the channel in question (in DISCORD's format)
		:param permission: the name of the permission to change
		:param value: the new state of the permission flag
		:returns: whether the flag did not already have that value
		"""
		db_channel = self.bot.db_session.get(p.Channel, channel.id)
		if db_channel is not None:
			if getattr(db_channel, permission) == value:
				# Flag already had this value
				return False
			# Set this now because it might not have been during the migrations
			db_channel.guild_id = channel.guild.id
		else:
			db_channel = p.Channel(id=channel.id, guild_id=channel.guild.id)
		setattr(db_channel, permission, value)
		self.bot.db_session.add(db_channel)
		# Flag's value is different now because of this call
		# (including if you create a new row just to set the flag to False)
		return True

	def has_permission(
		self, channel: discord.TextChannel, permission: Permission
	) -> bool:
		statement = sm.select(p.Channel.id).where(
			# TODO: works without the `== True`?
			p.Channel.id == channel.id,
			getattr(p.Channel, permission) == True,
		)
		return self.bot.db_session.exec(statement).first() is not None

	def get_webhook_id(self, channel: discord.TextChannel) -> Snowflake | None:
		statement = sm.select(p.Channel.webhook_id).where(
			p.Channel.id == channel.id
		)
		return self.bot.db_session.exec(statement).first()

	def set_webhook_id(
		self, channel: discord.TextChannel, webhook: discord.Webhook
	) -> None:
		statement = sm.select(p.Channel).where(p.Channel.id == channel.id)
		# not none: Parrot will only ever be making webhooks in channels where
		# it has speaking permission, and so a row for this channel will always
		# already exist in the database.
		db_channel = cast_not_none(self.bot.db_session.exec(statement).first())
		db_channel.webhook_id = webhook.id
		self.bot.db_session.add(db_channel)

	def delete(self, channel: discord.TextChannel) -> bool:
		db_channel = self.bot.db_session.get(p.Channel, channel.id)
		if db_channel is None:
			return False
		self.bot.db_session.delete(db_channel)
		return True
