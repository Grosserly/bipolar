import asyncio
from collections.abc import AsyncIterator
from typing import cast

import discord
from discord.ext import commands

from parrot.bot import Parrot
from parrot.utils import HistoryCrawler, ParrotEmbed, checks
from parrot.utils.converters import Memberlike
from parrot.utils.exceptions import (
	AlreadyScanning,
	ChannelTypeError,
	UserPermissionError,
)
from parrot.utils.types import AnyUser, Snowflake


class Quickstart(commands.Cog):
	def __init__(self, bot: Parrot):
		self.bot = bot
		# Keep track of Quickstart scans that are currently happening.
		# Contains user IDs
		self.ongoing_scans: set[Snowflake] = set()

	@staticmethod
	async def live_update_status(
		status_message: discord.Message,
		user: AnyUser,
		crawler: HistoryCrawler,
	) -> None:
		while crawler.running:
			embed = ParrotEmbed(
				description=(
					f"**Scanning across Parrot's servers...**\nCollected "
					f"{crawler.num_collected} new messages..."
				)
			)
			embed.set_author(
				name="Quickstart",
				icon_url="https://i.gifer.com/ZZ5H.gif",  # Loading spinner
			)
			embed.set_footer(
				text=f"Scanning for {user}",
				icon_url=user.display_avatar.url,
			)
			await status_message.edit(embed=embed)
			await asyncio.sleep(2)

	@commands.command()
	@commands.cooldown(2, 4, commands.BucketType.user)
	async def quickstart(
		self, ctx: commands.Context, user: Memberlike | None = None
	) -> None:
		"""
		Scrape your past messages in this server to get started using Parrot
		right away.
		"""
		# region resolve member
		if (
			not isinstance(ctx.channel, discord.TextChannel)
			or ctx.guild is None
		):
			raise ChannelTypeError("Quickstart is only available in servers.")
		member = cast(discord.Member | None, user)
		if member is None or ctx.author == member:
			member = cast(discord.Member, ctx.author)
		else:
			if not checks.is_admin(ctx):
				raise UserPermissionError(
					"You can only run Quickstart on yourself."
				)
			if not member.bot:
				raise UserPermissionError(
					"Quickstart can only be run on behalf of bots."
				)
		self.bot.crud.member.assert_registered(member)
		# endregion

		# You can only run one Quickstart scan at a time.
		if member.id in self.ongoing_scans:
			if ctx.author == member:
				raise AlreadyScanning("❌ Quickstart is already running!")
			raise AlreadyScanning(
				f"❌ Quickstart is already running for {member.mention}!"
			)

		self.ongoing_scans.add(member.id)

		# try-except so we can clear the user's scan status in case anything
		# goes wrong (and this cog has a long history of things going wrong)
		try:
			# Create an embed that will show the status of the Quickstart
			# operation and DM it to the user who invoked the command.
			embed = (
				ParrotEmbed(
					description=(
						"**Scanning across Parrot's servers...**\n"
						"Collected 0 new messages..."
					)
				)
				.set_author(
					name="Quickstart",
					icon_url="https://i.gifer.com/ZZ5H.gif",  # Loading spinner
				)
				.set_footer(
					text=f"Scanning for {member.mention}",
					icon_url=member.display_avatar.url,
				)
			)
			whose = (
				"your" if ctx.author.id == member.id else f"{member.mention}'s"
			)
			status_message = await ctx.author.send(embed=embed)
			await ctx.send(
				embed=ParrotEmbed(
					title="Quickstart is scanning",
					description=(
						"Parrot is now scanning this server and learning from "
						f"{whose} past messages.\nThis could take a few minutes."
						"\nCheck your DMs to see its progress."
					),
				),
				reference=ctx.message,
			)

			# Create an iterator representing up to 100,000 messages since the
			# user joined the server.
			histories: list[AsyncIterator[discord.Message]] = []
			learning_channel_ids = (
				self.bot.crud.guild.get_channel_ids_with_permission(
					ctx.guild, "can_learn_here"
				)
			)
			for channel_id in learning_channel_ids:
				channel = await self.bot.fetch_channel(channel_id)
				if not isinstance(channel, discord.TextChannel):
					continue
				try:
					member = await channel.guild.fetch_member(member.id)
				except discord.errors.NotFound:
					continue
				histories.append(
					channel.history(
						limit=100_000,
						after=member.joined_at,
					)
				)

			def crawler_action(message: discord.Message) -> bool:
				recorded = self.bot.crud.message.record(message)
				for _ in recorded:
					return True
				return False

			# Create an object that will scan through the server's message
			# history and learn from the messages this user has posted.
			crawler = HistoryCrawler(
				histories=histories,
				action=crawler_action,
				filter=lambda message: message.author.id == member.id,
				limit=100_000,
			)

			# In parallel, start the crawler and periodically update the
			# status_message with its progress.
			async with asyncio.TaskGroup() as tg:
				tg.create_task(
					Quickstart.live_update_status(
						status_message=status_message,
						user=member,
						crawler=crawler,
					)
				)
				tg.create_task(crawler.crawl())

			# Update the status embed one last time, but DELETE it this time and
			# post a brand new one so that the user gets a new notification.
			name = "you" if ctx.author == member else f"{member.mention}"
			embed = ParrotEmbed(
				description=(
					f"**Scan complete.**\nCollected "
					f"{crawler.num_collected} new messages."
				)
			)
			embed.set_author(name="✅ Quickstart")
			embed.set_footer(
				text=f"Scanning for {member.mention}",
				icon_url=member.display_avatar.url,
			)
			if crawler.num_collected == 0:
				embed.description += (
					# type: ignore  -- embed.description is definitely not None
					f"\n😕 Couldn't find any messages from {name}."
				)
				embed.color = ParrotEmbed.Color.Red.value
			asyncio.create_task(status_message.delete())
			asyncio.create_task(ctx.author.send(embed=embed))
		except:  # noqa - we really do want to just catch ANY error
			self.ongoing_scans.remove(member.id)
			raise

		self.ongoing_scans.remove(member.id)


async def setup(bot: Parrot) -> None:
	await bot.add_cog(Quickstart(bot))
