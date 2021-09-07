from typing import Any, Callable, Coroutine, NamedTuple
from utils.types import ModifiedAvatar
from discord import File, TextChannel, User
from asyncio.events import AbstractEventLoop
from aioredis import Redis
from aiohttp import ClientSession

import asyncstdlib as a
import ujson as json  # ujson is faster
from io import BytesIO
from PIL import Image, ImageOps

class ParrotInterface(NamedTuple):
    redis: Redis
    loop: AbstractEventLoop
    http_session: ClientSession
    fetch_channel: Callable[[int], Coroutine[Any, Any, TextChannel]]


class AvatarManager:
    AVATAR_DATABASE_CHANNEL_ID = 867573882608943127

    def __init__(self, bot: ParrotInterface):
        self.bot = bot


    @a.lru_cache(maxsize=5)
    async def fetch(self, user: User) -> str:
        ledger: ModifiedAvatar = {}
        response = await self.bot.redis.hget("avatars", str(user.id))
        avatar_channel = await self.bot.fetch_channel(self.AVATAR_DATABASE_CHANNEL_ID)

        if response is not None:
            ledger = json.loads(response)

            # User hasn't changed their avatar since last time they did
            # |imitate, so we can use the cached modified avatar.
            if str(user.avatar_url) == ledger["original_avatar_url"]:
                return ledger["modified_avatar_url"]
            
            # Respect the user's privacy by deleting the message with their old
            # avatar.
            # Don't wait for this operation to complete before continuing.
            self.bot.loop.create_task(
                self._delete_message(avatar_channel, ledger["source_message_id"])
            )
        
        # User has changed their avatar since last time they did |imitate or has
        # not done |imitate before, so we must create a modified version of
        # their avatar.
        # Ideally, we would just upload this modified avatar as the imitate
        # webhook's avatar directly, but Discord only accepts URLs for webhook
        # avatars, not files. So we must first upload the generated image to a
        # channel on Discord where we can then get the URL of the new avatar
        # to use in a webhook (Discord As A CDN!).
        # Oh well, at least we don't have to store the avatars ourselves now.
        modified_avatar = await self.modify_avatar(str(user.avatar_url))
        message = await avatar_channel.send(
            file=File(modified_avatar, f"{user.id}.webp")
        )

        # Update the avatar database with the new avatar URL.
        ledger["original_avatar_url"] = str(user.avatar_url)
        ledger["modified_avatar_url"] = message.attachments[0].url
        ledger["source_message_id"] = message.id
        self.bot.loop.create_task(
            self.bot.redis.hset("avatars", str(user.id), json.dumps(ledger))
        )

        return ledger["modified_avatar_url"]


    async def _delete_message(self, channel: TextChannel, message_id: int) -> None:
        message = await channel.fetch_message(message_id)
        await message.delete()


    async def modify_avatar(self, image_url: str) -> BytesIO:
        """
        Mirror and invert the avatar.
        For use as the avatar in an imitate message to distinguish them from
        messages from real users.
        """
        async with self.bot.http_session.get(image_url) as response:
            with Image.open(BytesIO(await response.read())) as image:
                image = ImageOps.mirror(image)
                image = ImageOps.invert(image)
                result = BytesIO()
                image.save(result, format="WEBP")
                result.seek(0)
                return result
