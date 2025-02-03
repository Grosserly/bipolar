"""
Minimal SQLModel setup to complete this migration.
Any table referred to in a foreign key must be present too.
"""

from enum import Enum

import sqlalchemy as sa
import sqlmodel as sm
from parrot.alembic.typess import PModel
from parrot.db import GuildMeta
from parrot.utils.types import Snowflake


__all__ = ["Channel", "Guild", "Member", "Message", "ErrorCode"]


class ErrorCode(Enum):
	"""Sentinel guild IDs to indicate different results for this migration."""

	UNPROCESSED = 0
	NOT_FOUND = -1
	REQUEST_FAILED = -2
	INVALID_TYPE = -3


class Channel(PModel, table=True):
	id: Snowflake = sm.Field(primary_key=True)
	can_speak_here: bool = False
	can_learn_here: bool = False
	webhook_id: Snowflake | None = None
	# New
	guild_id: Snowflake = sm.Field(foreign_key="guild.id")
	...


class Guild(PModel, table=True):
	id: Snowflake = sm.Field(primary_key=True)
	imitation_prefix: str = GuildMeta.default_imitation_prefix
	imitation_suffix: str = GuildMeta.default_imitation_suffix
	...


class Member(PModel, table=True):
	id: Snowflake = sm.Field(primary_key=True)
	wants_random_wawa: bool = True
	...


class Message(PModel, table=True):
	id: Snowflake = sm.Field(primary_key=True)
	content: str
	author_id: Snowflake = sm.Field(foreign_key="member.id")
	# New
	guild_id: Snowflake = sm.Field(foreign_key="guild.id")
	channel_id: Snowflake
	__table_args__ = (
		sa.Index("ix_guild_id_author_id", "guild_id", "author_id"),
	)
