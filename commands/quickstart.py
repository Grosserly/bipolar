from typing import Dict, List, Union
from discord import Guild, Member, Message, User
from bot import Parrot

import asyncio
import itertools
from discord.ext import commands
from utils.parrot_embed import ParrotEmbed
from utils.history_crawler import HistoryCrawler
from utils.exceptions import AlreadyScanning, UserPermissionError
from utils.checks import is_admin
from utils.converters import Userlike
from utils.exceptions import NotRegisteredError


class Quickstart(commands.Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        # Keep track of Quickstart scans that are currently happening.
        # Key: Guild ID
        # Value: List of User IDs, representing whom Quickstart is scanning for
        #        in this guild.
        self.ongoing_scans: Dict[int, List[int]] = {}


    async def live_update_status(
        self,
        source_guild: Guild,
        status_message: Message,
        user: User,
        crawler: HistoryCrawler
    ) -> None:
        while crawler.running:
            embed = ParrotEmbed(
                description=(
                    f"**Scanning {source_guild.name}...**\nCollected "
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
        self,
        ctx: commands.Context,
        user: Userlike=None
    ) -> None:
        """ Scan your past messages to get started using Parrot right away. """
        if user is None or ctx.author == user:
            user = ctx.author
        else:
            if not is_admin(ctx):
                raise UserPermissionError(
                    "You can only run Quickstart on yourself."
                )
            if not user.bot:
                raise UserPermissionError(
                    "Quickstart can only be run on behalf of bots."
                )

        self.assert_registered(user)

        if ctx.guild.id not in self.ongoing_scans:
            self.ongoing_scans[ctx.guild.id] = []

        # You can't run Quickstart in a server that Quickstart is already
        # currently scanning for you.
        if user.id in self.ongoing_scans[ctx.guild.id]:
            if ctx.author == user:
                raise AlreadyScanning(
                    "❌ You are already currently running Quickstart in this "
                    "server!"
                )
            raise AlreadyScanning(
                f"❌ Quickstart is already running for {user} in this server!"
            )

        # Record that Quickstart is scanning this guild for this user.
        self.ongoing_scans[ctx.guild.id].append(user.id)

        # Tell the user off if they try to run this command in a DM channel.
        if ctx.guild is None:
            await ctx.send(
                "Quickstart is only available in servers. Try running "
                "Quickstart again in a server that Parrot is in."
            )
            return

        # Create and embed that will show the status of the Quickstart
        # operation and DM it to the user who invoked the command.
        if ctx.author == user:
            name = "your"
        else:
            name = f"{user.mention}'s"
        embed = ParrotEmbed(
            description=(
                f"**Scanning {ctx.guild.name}...**\nCollected 0 new "
                "messages..."
            )
        )
        embed.set_author(
            name="Quickstart",
            icon_url="https://i.gifer.com/ZZ5H.gif",  # Loading spinner
        )
        embed.set_footer(
            text=f"Scanning for {user.mention}",
            icon_url=user.display_avatar.url,
        )
        status_message = await ctx.author.send(embed=embed)
        await ctx.send(embed=ParrotEmbed(
            title="Quickstart is scanning",
            description=(
                f"Parrot is now scanning this server and learning from {name} "
                "past messages.\nThis could take a few minutes.\nCheck your DMs"
                " to see its progress."
            )
        ), reference=ctx.message)

        # Create an iterator representing up to 100,000 messages since the user
        # joined the server.
        histories = []
        for channel_id in self.bot.learning_channels:
            histories.append(
                (await self.bot.fetch_channel(channel_id)).history(
                    limit=100_000,
                    after=user.joined_at,
                )
            )
        history = itertools.chain(*histories)

        # Create an object that will scan through the server's message history
        # and learn from the messages this user has posted.
        crawler = HistoryCrawler(
            history=history,
            action=self.bot.learn_from,
            filter=lambda message: message.author == user,
            limit=100_000,
        )

        # In parallel, start the crawler and periodically update the
        # status_message with its progress.
        asyncio.gather(
            self.live_update_status(
                source_guild=ctx.guild,
                status_message=status_message,
                user=user,
                crawler=crawler,
            ),
            crawler.crawl(),
        )

        # Update the status embed one last time, but DELETE it this time and
        #   post a brand new one so that the user gets a new notification.
        if ctx.author == user:
            name = "you"
        else:
            name = f"{user}"
        embed = ParrotEmbed(
            description=(
                f"**Scan in {ctx.guild.name} complete.**\nCollected "
                f"{crawler.num_collected} new messages."
            )
        )
        embed.set_author(name="✅ Quickstart")
        embed.set_footer(
            text=f"Scanning for {user}",
            icon_url=user.display_avatar.url,
        )
        if crawler.num_collected == 0:
            embed.description += (
                f"\n😕 Couldn't find any messages from {name} in this server."
            )
            embed.color = ParrotEmbed.colors["red"]
        await asyncio.gather(
            status_message.delete(),
            ctx.author.send(embed=embed)
        )

        self.ongoing_scans[ctx.guild.id].remove(user.id)
        if len(self.ongoing_scans[ctx.guild.id]) == 0:
            del self.ongoing_scans[ctx.guild.id]


    def assert_registered(self, user: Union[User, Member]) -> None:
        if not user.bot and user.id not in self.bot.registered_users:
            raise NotRegisteredError(
                f"User {user} is not registered. To register, read the privacy "
                f"policy with `{self.bot.command_prefix}policy`, then register "
                f"with `{self.bot.command_prefix}register`."
            )


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Quickstart(bot))
