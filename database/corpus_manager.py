from typing import Dict, List, NamedTuple, Union, cast
from discord import User, Member, Message
from utils.parrot_markov import ParrotMarkov
from aioredis import Redis
from database.redis_set import RedisSet
from exceptions import NoDataError, NotRegisteredError


class ParrotInterface(NamedTuple):
    redis: Redis
    registered_users: RedisSet
    get_model: ParrotMarkov
    command_prefix: str


class CorpusManager:
    def __init__(self, bot: ParrotInterface):
        self.bot = bot

    async def add(self, user: Union[User, Member], message: Message) -> None:
        """ Record a message to a user's corpus. """
        await self.assert_registered(user)

        # TODO: Uncomment when model.update() is implemented
        # model = await self.bot.get_model(user.id)

        for embed in message.embeds:
            desc = embed.description
            if isinstance(desc, str):
                message.content += " " + desc

        # Thank you to Litleck for the idea to include attachment URLs.
        for attachment in message.attachments:
            message.content += " " + attachment.url

        # model.update(message.content)

        await self.bot.redis.hset(
            name=f"corpus:{user.id}",
            key=str(message.id),
            value=message.content,
        )

    async def get(self, user: Union[User, Member]) -> List[str]:
        """ Get a corpus from the source of truth by user ID. """
        await self.assert_registered(user)
        corpus = cast(List[str], await self.bot.redis.hvals(f"corpus:{user.id}"))
        if len(corpus) == 0:
            raise NoDataError(f"No data available for user {user}.")
        return corpus

    async def get_dict(self, user: Union[User, Member]) -> Dict[int, str]:
        """ Get a corpus by user ID as a "message_id: message" dict. """
        await self.assert_registered(user)
        key_vals = cast(List[str], await self.bot.redis.hgetall(f"corpus:{user.id}"))
        if len(key_vals) == 0:
            raise NoDataError(f"No data available for user {user}.")
        corpus: Dict[int, str] = {}
        for i in range(0, len(key_vals), 2):
            corpus[int(key_vals[i])] = key_vals[i + 1]
        return corpus

    async def delete(self, user: Union[User, Member]) -> None:
        """ Delete a corpus from the source of truth. """
        num_deleted = cast(int, await self.bot.redis.delete(f"corpus:{user.id}"))
        if num_deleted == 0:
            raise NoDataError(f"No data available for user {user}.")

    async def delete_message(self, user: Union[User, Member], message_id: int) -> None:
        """ Delete a message (or list of messages) from a corpus. """
        num_deleted = cast(int, await self.bot.redis.hdel(f"corpus:{user.id}", str(message_id)))
        if num_deleted == 0:
            raise NoDataError(f"No data available for user {user}.")

    async def has(self, user: object) -> bool:
        """ Check if a user's corpus is present on the source of truth. """
        return (
            (isinstance(user, User) or isinstance(user, Member)) and
            bool(await self.bot.redis.exists(f"corpus:{user.id}"))
        )

    async def assert_registered(self, user: Union[User, Member]) -> None:
        if not user.bot and not (await self.bot.registered_users.has(user.id)):
            raise NotRegisteredError(f"User {user} is not registered. To register, read the privacy policy with `{self.bot.command_prefix}policy`, then register with `{self.bot.command_prefix}register`.")
