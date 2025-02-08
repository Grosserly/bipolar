import datetime as dt
from collections.abc import Sequence
from typing import cast

import discord
import sqlmodel as sm
from sqlalchemy import ScalarResult

import parrot.db.models as p
from parrot import config
from parrot.utils.types import Permission, Snowflake

from .types import SubCRUD


class CRUDGuild(SubCRUD):
	def get_channel_ids_with_permission(
		self, guild: discord.Guild, permission: Permission
	) -> ScalarResult[Snowflake]:
		statement = sm.select(p.Channel.id).where(
			p.Channel.guild_id == guild.id,
			getattr(p.Channel, permission) == True,
			# TODO: does this work?
			# getattr(p.Channel, permission),
		)
		return self.bot.db_session.exec(statement)

	def get_prefix(self, guild: discord.Guild) -> str:
		statement = sm.select(p.Guild.imitation_prefix).where(
			p.Guild.id == guild.id
		)
		return (
			self.bot.db_session.exec(statement).first()
			or p.GuildMeta.default_imitation_prefix
		)

	def set_prefix(self, guild: discord.Guild, new_prefix: str) -> None:
		db_guild = self.bot.db_session.get(p.Guild, guild.id) or p.Guild(
			id=guild.id, imitation_prefix=new_prefix
		)
		db_guild.imitation_prefix = new_prefix
		self.bot.db_session.add(db_guild)

	def get_suffix(self, guild: discord.Guild) -> str:
		statement = sm.select(p.Guild.imitation_suffix).where(
			p.Guild.id == guild.id
		)
		return (
			self.bot.db_session.exec(statement).first()
			or p.GuildMeta.default_imitation_suffix
		)

	def set_suffix(self, guild: discord.Guild, new_suffix: str) -> None:
		db_guild = self.bot.db_session.get(p.Guild, guild.id) or p.Guild(
			id=guild.id, imitation_suffix=new_suffix
		)
		db_guild.imitation_suffix = new_suffix
		self.bot.db_session.add(db_guild)

	async def get_registered_member_ids(
		self, guild: discord.Guild
	) -> Sequence[Snowflake]:
		return cast(
			Sequence[Snowflake],
			self.bot.db_session.exec(
				sm.select(p.Membership.user_id).where(
					p.Membership.guild_id == guild.id,
					p.Membership.is_registered == True,
				)
			).all()
			or [],
		)

	async def prune_expired_memberships(self) -> None:
		now = discord.utils.time_snowflake(dt.datetime.now())
		statement = sm.select(p.Membership).where(
			sm.col(p.Membership.ended_since).is_not(None),
			(
				now - sm.col(p.Membership.ended_since)
				> config.message_retention_period_seconds
			),
		)
		expired_memberships = self.bot.db_session.exec(statement)

		for membership in expired_memberships:
			try:
				guild = self.bot.get_guild(membership.guild.id)
				if guild is None:
					# TODO: what do here
					# Also delete this db guild?
					raise Exception()
				await guild.fetch_member(membership.user.id)
			except discord.NotFound:
				# User is truly not in this guild anymore
				await self.bot.crud.member.raw_delete_membership(membership)
			else:
				# User is actually still in this guild after all
				membership.ended_since = None
				self.bot.db_session.add(membership)

	def delete(self, guild: discord.Guild) -> bool:
		db_guild = self.bot.db_session.get(p.Guild, guild.id)
		if db_guild is None:
			return False
		self.bot.db_session.delete(db_guild)
		return True
