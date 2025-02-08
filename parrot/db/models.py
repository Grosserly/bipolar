"""
Parrot's database models, using SQLModel.

This is essentially a local cache of data from the Discord API that Parrot
relies on, plus some of Parrot's own information.

N.B. The primary keys on tables that are direct analogs to Discord entities
(e.g., Channel, Message) are intentionally _not_ created automatically by the
database, and are expected to be the same as their IDs from Discord.
"""

# TODO: Feasible to keep all Markov chain generators in the database,
# remove the in-memory cache?
# NOTE: sa.PickleType?

# TODO: understand .commit() and .refresh()/see if there are any occurrences
# that can be deleted

# TODO: prune unused Relationships and back-populations

import sqlalchemy as sa
from sqlmodel import Field, Relationship, SQLModel

from parrot.db import NAMING_CONVENTION, GuildMeta
from parrot.utils.types import Snowflake


SQLModel.metadata.naming_convention = NAMING_CONVENTION


class Channel(SQLModel, table=True):
	id: Snowflake = Field(primary_key=True)
	can_speak_here: bool = False
	can_learn_here: bool = False
	webhook_id: Snowflake | None = None
	guild_id: Snowflake = Field(foreign_key="guild.id")

	# Explicit Channel delete conditions:
	# - Channel is deleted on Discord
	# Cascades:
	# - Losing a channel does not mean losing the guild
	# - Losing a channel loses all the messages therein
	messages: list["Message"] = Relationship(cascade_delete=True)


class Message(SQLModel, table=True):
	id: Snowflake = Field(primary_key=True)
	content: str
	author_id: Snowflake = Field(foreign_key="user.id")
	channel_id: Snowflake = Field(foreign_key="channel.id")
	guild_id: Snowflake = Field(foreign_key="guild.id")
	# Messages are going to be SELECTed almost exclusively by these columns, so
	# declare an index for them
	__table_args__ = (
		sa.Index("ix_guild_id_author_id", "guild_id", "author_id"),
	)

	# Explicit Message delete conditions:
	# - Message is deleted on Discord
	# Cascades:
	# - None


class Membership(SQLModel, table=True):
	"""User-Guild relationship"""

	user_id: Snowflake | None = Field(
		default=None, foreign_key="user.id", primary_key=True
	)
	guild_id: Snowflake | None = Field(
		default=None, foreign_key="guild.id", primary_key=True
	)
	is_registered: bool = False
	# Timestamp denoting when a user left this guild.
	# None if the user is still there.
	ended_since: Snowflake | None = None

	# Explicit Membership delete conditions:
	# - User has been gone from a guild for long enough, so Parrot autoforgets
	#   - NOT immediately after a user leaves a guild
	# - (TODO) user does a guild-specific version of |forget me
	# Cascades:
	# - Concluding a user will not rejoin a guild does not mean the user does
	#   not exist anymore
	# - Concluding a user will not rejoin a guild does not mean the guild does
	#   not exist anymore
	# - If a user is not in a guild anymore, then we should forget the
	#   corresponding Antiavatar
	# - All messages from this user in this guild should be forgotten
	user: "User" = Relationship(back_populates="memberships")
	guild: "Guild" = Relationship(back_populates="memberships")
	antiavatar: "Antiavatar | None" = Relationship(cascade_delete=True)
	messages: list[Message] = Relationship(cascade_delete=True)


class User(SQLModel, table=True):
	id: Snowflake = Field(primary_key=True)
	wants_random_wawa: bool = True

	# Explicit User delete conditions:
	# - User does |forget me
	# - User leaves all guilds in common with Parrot
	# - User is deleted on Discord (which just manifests as the previous one)
	# Cascades:
	# - Forgetting a user means forgetting their guild memberships
	#   - Associated avatar and messages deleted on cascade in Membership table
	memberships: list[Membership] = Relationship(
		back_populates="user",
		cascade_delete=True,
	)


class Guild(SQLModel, table=True):
	id: Snowflake = Field(primary_key=True)
	imitation_prefix: str = GuildMeta.default_imitation_prefix
	imitation_suffix: str = GuildMeta.default_imitation_suffix

	# Explicit Guild delete conditions:
	# - Guild is deleted on Discord
	# Cascades:
	# - A guild being deleted deletes the channels therein
	# - A guild being deleted deletes the membership relations therein
	# - Messages deleted in Membership cascade
	memberships: list[Membership] = Relationship(
		back_populates="guild", cascade_delete=True
	)
	channels: list[Channel] = Relationship(cascade_delete=True)


class AntiavatarBase(SQLModel):
	original_url: str
	url: str
	message_id: Snowflake


# TODO (optimization): merge these across guilds for users who don't use
# guild-specific avatars/don't have Premium
class Antiavatar(AntiavatarBase, table=True):
	"""Avatar info linked to a Membership"""

	user_id: Snowflake = Field(foreign_key="user.id", primary_key=True)
	guild_id: Snowflake = Field(foreign_key="guild.id", primary_key=True)


class AntiavatarCreate(AntiavatarBase):
	pass
