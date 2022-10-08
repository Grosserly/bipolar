from typing import Dict, List, Union
from discord import ChannelType, Member, Message, TextChannel, User
from bot import Parrot

import asyncio
from discord.ext import commands
from utils.parrot_embed import ParrotEmbed
from utils.channel_crawler import ChannelCrawler
from utils.exceptions import AlreadyScanning, UserPermissionError
from utils.checks import is_admin
from utils.converters import Userlike
from utils import Paginator
from utils.exceptions import NotRegisteredError


class Quickstart(commands.Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        # Keep track of Quickstart scans that are currently happening.
        # Key: Channel ID
        # Value: List of User IDs, representing whom Quickstart is scanning for
        #        in this channel.
        self.ongoing_scans: Dict[int, List[int]] = {}


    async def live_update_status(
        self,
        source_channel: TextChannel,
        status_message: Message,
        user: User,
        crawler: ChannelCrawler
    ) -> None:
        while crawler.running:
            embed = ParrotEmbed(
                description=(
                    f"**Scanning {source_channel.mention}...**\nCollected "
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

        if ctx.channel.id not in self.ongoing_scans:
            self.ongoing_scans[ctx.channel.id] = []

        # You can't run Quickstart in a channel that Quickstart is already
        #   currently scanning for you.
        if user.id in self.ongoing_scans[ctx.channel.id]:
            if ctx.author == user:
                raise AlreadyScanning(
                    "❌ You are already currently running Quickstart in this "
                    "channel!"
                )
            raise AlreadyScanning(
                f"❌ Quickstart is already running for {user} in this channel!"
            )

        # Record that Quickstart is scanning this channel for this user.
        self.ongoing_scans[ctx.channel.id].append(user.id)

        # Tell the user off if they try to run this command in a DM channel.
        if ctx.channel.type != ChannelType.text:
            await ctx.send(
                "Quickstart is only available in servers. Try running "
                "Quickstart again in a server that Parrot is in."
            )
            return

        # Show the user where they can use Quickstart within this server if they
        #   use the command in a channel where Parrot can't learn.
        if ctx.channel.id not in self.bot.learning_channels:
            embed = ParrotEmbed(
                title="Quickstart Channels",
                description=(
                    "Quickstart is available in channels where Parrot can learn"
                    " from your messages. Try running Quickstart again in one "
                    "of these channels:"
                )
            )
            channel_mentions = []
            for channel in ctx.guild.channels:
                if channel.id in self.bot.learning_channels:
                    channel_mentions.append(channel.mention)
            if len(channel_mentions) == 0:
                embed.description = "None"
                await ctx.send(embed=embed)
                return

            paginator = Paginator.FromList(
                ctx,
                entries=channel_mentions,
                template_embed=embed,
            )
            await paginator.run()
            return

        # Create and embed that will show the status of the Quickstart
        #   operation and DM it to the user who invoked the command.
        if ctx.author == user:
            name = "your"
        else:
            name = f"{user.mention}'s"
        embed = ParrotEmbed(
            description=(
                f"**Scanning {ctx.channel.mention}...**\nCollected 0 new "
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
                f"Parrot is now scanning this channel and learning from {name} "
                "past messages.\nThis could take a few minutes.\nCheck your DMs"
                " to see its progress."
            )
        ), reference=ctx.message)

        # Create an iterator representing this channel's past messages.
        history = ctx.channel.history(
            limit=100_000,
            after=user.joined_at,
        )

        # Create an object that will scan through the channel's message history
        # and learn from the messages this user has posted.
        crawler = ChannelCrawler(
            history=history,
            action=self.bot.learn_from,
            filter=lambda message: message.author == user,
        )

        # In parallel, start the crawler and periodically update the
        # status_message with its progress.
        asyncio.create_task(crawler.crawl())
        asyncio.create_task(
            self.live_update_status(
                source_channel=ctx.channel,
                status_message=status_message,
                user=user,
                crawler=crawler,
            )
        )

        # Update the status embed one last time, but DELETE it this time and
        #   post a brand new one so that the user gets a new notification.
        if ctx.author == user:
            name = "you"
        else:
            name = f"{user}"
        embed = ParrotEmbed(
            description=(
                f"**Scan in {ctx.channel.mention} complete.**\nCollected "
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
                f"\n😕 Couldn't find any messages from {name} in this channel."
            )
            embed.color = ParrotEmbed.colors["red"]
        await asyncio.gather(
            status_message.delete(),
            ctx.author.send(embed=embed)
        )

        self.ongoing_scans[ctx.channel.id].remove(user.id)
        if len(self.ongoing_scans[ctx.channel.id]) == 0:
            del self.ongoing_scans[ctx.channel.id]


    def assert_registered(self, user: Union[User, Member]) -> None:
        if not user.bot and user.id not in self.bot.registered_users:
            raise NotRegisteredError(
                f"User {user} is not registered. To register, read the privacy "
                f"policy with `{self.bot.command_prefix}policy`, then register "
                f"with `{self.bot.command_prefix}register`."
            )


async def setup(bot: Parrot) -> None:
    await bot.add_cog(Quickstart(bot))
