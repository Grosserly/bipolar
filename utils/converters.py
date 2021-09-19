import re
from discord.ext import commands
from discord import User

from discord.errors import NotFound
from exceptions import UserNotFoundError


class Userlike(commands.Converter):
    """
    A string that can resolve to a User.
    Works with:
        - Mentions, like <@394750023975409309> and <@!394750023975409309>
        - User IDs, like 394750023975409309
        - The string "me" or "myself", which resolves to the context's author
        - The string "you", "yourself", or "previous" which resolves to the last
              person to speak in the channel
    """

    async def convert(self, ctx: commands.Context, text: str=None) -> User:
        # Use this error if anything goes wrong.
        user_not_found = UserNotFoundError(f'User "{text}" does not exist.')

        if text is None:
            raise user_not_found

        text = text.lower()

        if text in ("me", "myself"):
            return ctx.author

        # Get the author of the last message send in the channel who isn't
        # Parrot or the person who sent this command.
        if text in ("you", "yourself", "previous"):
            async for message in ctx.channel.history(before=ctx.message):
                if message.author not in (ctx.bot.user, ctx.author) and message.webhook_id is None:
                    if ctx.guild:
                        return ctx.guild.get_member(ctx.author.id)  # Channel history doesn't preserve nicknames 🤷‍♂️
                    else:
                        return message.author

        # If this is not a guild, it must be a DM channel, and therefore the
        #   only person you can imitate is yourself.
        if ctx.guild is None:
            raise user_not_found

        # Strip the mention down to an ID.
        try:
            user_id = int(re.sub("[^0-9]", "", text))
        except ValueError:
            raise user_not_found

        # Fetch the member by ID.
        try:
            return await ctx.guild.fetch_member(user_id)
        except NotFound:
            raise user_not_found
