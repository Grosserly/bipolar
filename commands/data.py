from utils.types import PendingConfirmations
from bot import Parrot

import asyncio
from discord.ext import commands
from utils.parrot_embed import ParrotEmbed
from io import BytesIO
import ujson as json  # ujson is faster
from exceptions import NoDataError, UserPermissionError, UserNotFoundError
from utils.converters import Userlike


class Data(commands.Cog):
    def __init__(self, bot: Parrot):
        self.pending_confirmations: PendingConfirmations = {}
        self.bot = bot


    @commands.command(aliases=["checkout"])
    @commands.cooldown(2, 3600, commands.BucketType.user)
    async def download(self, ctx: commands.Context) -> None:
        """ Download a copy of your data. """
        user = ctx.author

        # Upload to file.io, a free filesharing service where the file is
        #   deleted once it's downloaded.
        corpus = await self.bot.corpora.get(user)
        with BytesIO(json.dumps(corpus).encode()) as fp:
            async with self.bot.http_session.post(
                "https://file.io/",
                data={
                    "file": fp,
                    "expiry": "6h",
                }
            ) as response:
                download_url = (await response.json())["link"]

        # DM the user their download link.
        embed_download_link = ParrotEmbed(
            title="Link to download your data",
            description=download_url,
        )
        embed_download_link.set_footer(text="Link expires in 6 hours.")
        await user.send(embed=embed_download_link)

        # Tell them to check their DMs.
        embed_download_ready = ParrotEmbed(
            title="Download ready",
            color_name="green",
            description="A link to download your data has been DM'd to you.",
        )
        await ctx.send(embed=embed_download_ready)


    @commands.group()
    @commands.cooldown(2, 4, commands.BucketType.user)
    async def forget(self, ctx: commands.Context, maybe_user: str=None, *args) -> None:
        """ Make Parrot delete all the data it has about you. """
        if maybe_user is not None:
            try:
                userlike = Userlike()
                user = await userlike.convert(ctx, maybe_user)
            except UserNotFoundError:
                for command in self.forget.commands:
                    if command.name == maybe_user:
                        await command(ctx, *args)
                        return
                raise
        else:
            user = ctx.author

        if user != ctx.author and ctx.author.id not in self.bot.owner_ids:
            raise UserPermissionError("You are not allowed to make Parrot forget other users.")

        if not await self.bot.corpora.has(user):
            raise NoDataError(f"No data available for user {user}.")

        confirm_code = ctx.message.id

        # Keep track of this confirmation by storing some information about it
        #   in a dict.
        self.pending_confirmations[confirm_code] = {
            "author": ctx.author,
            "corpus_owner": user,
        }

        embed = ParrotEmbed(
            title="Are you sure?",
            description=f"This will permantently delete the data of {user}.\nTo confirm, paste the following command:\n`{self.bot.command_prefix}forget confirm {confirm_code}`",
            color_name="orange",
        )
        embed.set_footer(text="Action will be automatically canceled in 1 minute.")

        await ctx.send(embed=embed, reference=ctx.message)

        # Delete the confirmation after 1 minute.
        await asyncio.sleep(60)
        try:
            del self.pending_confirmations[confirm_code]
        except KeyError:
            pass


    @forget.command(name="confirm", hidden=True)
    @commands.cooldown(2, 4, commands.BucketType.user)
    async def forget_confirm(self, ctx: commands.Context, confirm_code: int) -> None:
        # You'd think that since this argument is typed as an int, it would come
        #   in as an int. But noooo, it actually comes in as a string.
        confirm_code = int(confirm_code)
        confirmation = self.pending_confirmations.get(confirm_code, None)
        
        confirmation_is_valid = (
            confirmation is not None and
            confirmation["author"] == ctx.author
        )

        if confirmation_is_valid:
            user = confirmation["corpus_owner"]

            # Delete the user's corpus.
            await self.bot.corpora.delete(user)

            # Invalidate this confirmation code
            del self.pending_confirmations[confirm_code]

            await ctx.send(embed=ParrotEmbed(
                title=f"Parrot has forgotten {user}.",
                description="All of the data that Parrot has collected from this user has been deleted.",
                color_name="gray",
            ), reference=ctx.message)
        else:
            await ctx.send(f"Confirmation code `{confirm_code}` is invalid.")


def setup(bot: Parrot) -> None:
    bot.add_cog(Data(bot))
