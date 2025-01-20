from collections.abc import Iterable
from typing import TYPE_CHECKING, cast

import discord

import parrot.db.models as p
from parrot import config
from parrot.utils.types import Snowflake
from parrot.utils import cast_not_none, regex

from .types import SubCRUD


if TYPE_CHECKING:
	from parrot.bot import Parrot


class CRUDMessage(SubCRUD):
	def __init__(
		self,
		bot: "Parrot"
	):
		super().__init__(bot)

	@staticmethod
	def _extract_text(message: discord.Message) -> str:
		for embed in message.embeds:
			if embed.description is not None:
				message.content += "\n" + embed.description
		for attachment in message.attachments:
			message.content += " " + attachment.url
		return message.content

	def validate_message(self, message: discord.Message) -> bool:
		"""
		A message must pass all of these checks before Parrot can learn from it.
		"""
		return (
			# Text content not empty.
			len(message.content) > 0
			and
			# Not a Parrot command.
			not message.content.startswith(config.command_prefix)
			and
			# Only learn in text channels, not DMs (or anywhere else).
			isinstance(message.channel, discord.TextChannel)
			and
			# Most bots' commands start with non-alphanumeric characters, so if
			# a message starts with one other than a known Markdown character or
			# special Discord character, Parrot should just avoid it because
			# it's probably a command.
			(
				message.content[0].isalnum()
				or bool(regex.discord_string_start.match(message.content[0]))
				or bool(regex.markdown.match(message.content[0]))
			)
			and
			# Don't learn from self.
			message.author.id != cast_not_none(self.bot.user).id
			and
			# Don't learn from Webhooks.
			message.webhook_id is None
			and
			# Parrot must be allowed to learn in this channel.
			self.bot.crud.channel.has_permission(message.channel, "can_learn_here")
			and
			# People will often say "v" or "z" on accident while spamming,
			# and it doesn't really make for good learning material.
			message.content not in ("v", "z")
		)

	def record(
		self, messages: discord.Message | list[discord.Message]
	) -> Iterable[discord.Message]:
		"""
		Add a Message or list of Messages to a user's corpus.
		Every Message in the list must be from the same user.
		:pre: message.author is a discord.Member
		"""
		# Ensure that messages is a list.
		# If it's not, just make it a list with one value.
		if not isinstance(messages, list):
			messages = [messages]

		member = cast(discord.Member, messages[0].author)
		if not self.bot.crud.member.is_registered(member):
			return []

		# Every message in the list must have the same author, because the
		# Corpus Manager adds every message passed to it to the same user.
		for message in messages:
			if message.author != member:
				raise ValueError(
					"Too many authors; every message passed in one call to"
					"record() must have the same author."
				)

		# Filter out any messages that don't pass all of validate_message()'s
		# checks.
		messages_filtered = filter(self.validate_message, messages)

		# Convert the messages to the database's format and add them to this
		# user's corpus.
		db_messages = (
			p.Message(
				id=m.id,
				author_id=member.id,
				guild_id=member.guild.id,
				timestamp=m.created_at,
				content=CRUDMessage._extract_text(m),
			)
			for m in messages_filtered
		)
		self.bot.db_session.add_all(db_messages)
		self.bot.db_session.commit()

		return messages_filtered

		# for message in messages:
		# 	self.bot.db_session.refresh(message)
		# if len(messages) > 0:
		# 	return self.corpora.add(user, messages)
		# return 0

	def delete(self, message_id: Snowflake) -> p.Message | None:
		"""Delete a message from the database."""
		db_message = self.bot.db_session.get(p.Message, message_id)
		if db_message is None:
			return None
		self.bot.db_session.delete(db_message)
		self.bot.db_session.commit()
		return db_message
