"""add channel and message guild id

Adds key guild_id to tables channel and message,
Adds indices to message.guild_id + author_id.

Scrapes these guild IDs from Discord.

Revision ID: 7d0ffe4179c6
Revises: 2e2045b63d7a
Create Date: 2025-01-21 14:40:18.601522

"""

import logging
from collections.abc import Sequence

import discord
import sqlalchemy as sa
import sqlmodel as sm
from parrot import config
from parrot.alembic.common import cleanup_models, count
from parrot.utils import cast_not_none
from tqdm import tqdm

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "7d0ffe4179c6"
down_revision: str | None = "2e2045b63d7a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	from parrot.alembic.models import r7d0ffe4179c6
	from parrot.alembic.models.r7d0ffe4179c6 import ErrorCode

	with op.batch_alter_table("channel") as batch_op:
		# https://stackoverflow.com/a/6710280
		# sqlite oversight: You have to add the column with a default value then
		# remove the default value after for it to work
		batch_op.add_column(
			sa.Column(
				"guild_id",
				sa.BigInteger(),
				nullable=False,
				server_default=str(ErrorCode.UNPROCESSED.value),
			)
		)
	with op.batch_alter_table("channel") as batch_op:
		batch_op.alter_column("guild_id", server_default=None)
		batch_op.create_foreign_key(None, "guild", ["guild_id"], ["id"])

	with op.batch_alter_table("message") as batch_op:
		batch_op.add_column(
			sa.Column(
				"guild_id",
				sa.BigInteger(),
				nullable=False,
				# Temporary default
				server_default=str(ErrorCode.UNPROCESSED.value),
			)
		)
		# Developing this migration has made me realize Parrot sorely needs
		# channel ID too to be able to remotely efficiently get further
		# information from messages
		batch_op.add_column(
			sa.Column(
				"channel_id",
				sa.BigInteger(),
				nullable=False,
				# Temporary default
				server_default=str(ErrorCode.UNPROCESSED.value),
			)
		)
		batch_op.create_foreign_key(None, "guild", ["guild_id"], ["id"])
		batch_op.create_index(
			op.f("ix_guild_id_author_id"), ["guild_id", "author_id"]
		)

	global target_metadata
	target_metadata = sm.SQLModel.metadata
	session = sm.Session(bind=op.get_bind())

	client = discord.Client(intents=discord.Intents.default())

	async def process_channels() -> list[discord.TextChannel]:
		db_channels = session.exec(
			sm.select(r7d0ffe4179c6.Channel).where(
				# TODO: works without the == True?
				r7d0ffe4179c6.Channel.can_learn_here == True  # noqa: E712
			)
		).all()
		channels: list[discord.TextChannel] = []
		for db_channel in tqdm(db_channels, desc="Channels processed"):
			try:
				channel = await client.fetch_channel(db_channel.id)
			except Exception as exc:
				logging.warning(
					f"Failed to fetch channel {db_channel.id}: {exc}"
				)
				db_channel.guild_id = ErrorCode.REQUEST_FAILED.value
				session.add(db_channel)
				continue
			if not isinstance(channel, discord.TextChannel):
				logging.warning(
					f"Invalid channel type: {db_channel.id} is {type(channel)}"
				)
				db_channel.guild_id = ErrorCode.INVALID_TYPE.value
				session.add(db_channel)
				continue
			logging.debug(
				f"Channel {db_channel.id} in guild {db_channel.guild_id}"
			)
			db_channel.guild_id = channel.guild.id
			channels.append(channel)
			session.add(db_channel)
		return channels

	async def process_messages(channels: list[discord.TextChannel]) -> None:
		"""
		Scattershot scraping strategy: process chunks of 100 messages all over
		Discord around relevant messages.
		Collect every relevant message's guild and channel ID, while staying as
		gracious to Discord's API as we can. Using the history API, we can pick
		up up to 100 relevant messages per API call. By only calling it around
		messages we know we need to process (as opposed to using just one
		history iterator per channel and scanning the entire thing), we will
		probably end up skipping chunks of messages we don't need to process,
		further reducing API calls.
		In a very large channel with many relevant messages, this could save
		hours. In a very large channel with few relevant messages, this could
		save days.
		Unfortunately, since we don't know which channel any message is in, we
		have to look for it in every channel Parrot can learn in.
		Still, these calls _may_ end up finding other relevant messages.
		"""
		db_messages_count = count(session, r7d0ffe4179c6.Message.id)
		# Progress bar
		with tqdm(total=db_messages_count, desc="Messages processed") as t:
			# Pick an unprocessed message. Which one, doesn't matter.
			statement = (
				sm.select(r7d0ffe4179c6.Message)
				.where(r7d0ffe4179c6.Message.guild_id == 0)
				.limit(1)
			)
			# Repeat until all messages from the database are processed.
			while (db_message := session.exec(statement).first()) is not None:
				# Look for the message in every learning channel.
				for channel in channels:
					try:
						# Get a chunk of messages around the chosen message.
						# The chosen message is relevant, and chances are ones
						# near it are too.
						# The largest chunk we can get from Discord's API in one
						# call is 100.
						messages = [
							message
							async for message in channel.history(
								limit=100, around=db_message
							)
						]
					except Exception as exc:
						logging.warning(
							"Request for messages around"
							f"{channel.guild.id}/{channel.id}/{db_message.id} "
							f"failed: {exc}"
						)
						db_message.guild_id = ErrorCode.REQUEST_FAILED.value
						t.update()
						continue
					message_ids = (message.id for message in messages)
					# Get any yet-unprocessed messages from the database that
					# match the ones in the chunk.
					db_messages = session.exec(
						sm.select(r7d0ffe4179c6.Message).where(
							sm.col(r7d0ffe4179c6.Message.id).in_(message_ids),
							r7d0ffe4179c6.Message.guild_id == 0,
						)
					)
					# Fill in the guild IDs and channel IDs for those messages
					# in the database.
					for db_message, message in zip(db_messages, messages):
						# message.guild guaranteed to exist because we got it
						# from a guild
						db_message.guild_id = cast_not_none(message.guild).id
						db_message.channel_id = message.channel.id
						session.add(db_message)
						logging.debug(
							f"Message {db_message.id} in guild/channel "
							f"{db_message.guild_id}/{db_message.channel_id}"
						)
						t.update()
				if db_message.guild_id == ErrorCode.UNPROCESSED.value:
					# Very important failsafe otherwise we may get stuck
					# selecting the same unprocessable message over and over
					logging.warning(
						f"Message {db_message.id} not found in learning "
						"channels"
					)
					db_message.guild_id = db_message.channel_id = (
						ErrorCode.NOT_FOUND.value
					)
					t.update()
					session.add(db_message)
				session.commit()

	@client.event
	async def on_ready() -> None:
		logging.info("Scraping Discord to populate guild IDs...")
		try:
			channels = await process_channels()
			await process_messages(channels)
		except Exception as exc:
			session.commit()
			logging.error(exc)
		await client.close()

	client.run(config.discord_bot_token)

	# Remove the temporary default value settings from message.guild_id and
	# channel_id now that they should have all been populated
	with op.batch_alter_table("message") as batch_op:
		batch_op.alter_column("guild_id", server_default=None)
		batch_op.alter_column("channel_id", server_default=None)

	cleanup_models(r7d0ffe4179c6)


def downgrade() -> None:
	try:
		with op.batch_alter_table("channel") as batch_op:
			batch_op.drop_constraint(
				op.f("fk_channel_guild_id_guild"), type_="foreignkey"
			)
			batch_op.drop_index(op.f("ix_guild_id_author_id"))
	except ValueError as exc:
		logging.warning(exc)
	with op.batch_alter_table("channel") as batch_op:
		batch_op.drop_column("guild_id")

	with op.batch_alter_table("message") as batch_op:
		batch_op.drop_constraint(
			op.f("fk_message_guild_id_guild"), type_="foreignkey"
		)
		batch_op.drop_column("guild_id")
