import sqlmodel as sm
from parrot.alembic.common import PModel
from parrot.db import GuildMeta
from parrot.utils.types import Snowflake


__all__ = ["User", "Guild", "Membership"]


class User(PModel, table=True):
	id: Snowflake = sm.Field(primary_key=True)
	wants_random_wawa: bool = True
	memberships: list["Membership"] = sm.Relationship(
		back_populates="user",
		cascade_delete=True,
	)
	...


class Guild(PModel, table=True):
	id: Snowflake = sm.Field(primary_key=True)
	imitation_prefix: str = GuildMeta.default_imitation_prefix
	imitation_suffix: str = GuildMeta.default_imitation_suffix
	memberships: list["Membership"] = sm.Relationship(back_populates="guild")
	...


class Membership(PModel, table=True):
	user_id: Snowflake | None = sm.Field(
		default=None, foreign_key="user.id", primary_key=True
	)
	guild_id: Snowflake | None = sm.Field(
		default=None, foreign_key="guild.id", primary_key=True
	)
	is_registered: bool = False
	user: User = sm.Relationship(back_populates="memberships")
	guild: Guild = sm.Relationship(back_populates="memberships")
