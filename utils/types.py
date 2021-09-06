import sys

if sys.version_info >= (3, 8):
    from typing import TypedDict  # pylint: disable=no-name-in-module
else:
    from typing_extensions import TypedDict

from typing import Dict, NamedTuple
import abc
from discord import Message, User
import aiohttp
from database.avatar_manager import AvatarManager
from database.corpus_manager import CorpusManager
from discord.ext.commands import AutoShardedBot
from aioredis import Redis
from database.redis_set import RedisSet
from utils.parrot_markov import ParrotMarkov


class ConfirmationBody(NamedTuple):
    author: User  # The forget command message's author
    corpus_owner: User  # User for whose the corpus to be forgotten

# Key: Message ID of a forget command
PendingConfirmations = Dict[int, ConfirmationBody]


class ModifiedAvatar(TypedDict):
    original_avatar_url: str
    modified_avatar_url: str
    source_message_id: int


class ParrotInterface(AutoShardedBot, metaclass=abc.ABCMeta):
    @classmethod
    def __subclasshook__(cls, subclass):
        return (
            hasattr(subclass, "get_model") and
            callable(subclass.get_model) and
            hasattr(subclass, "validate_message") and
            callable(subclass.validate_message) and
            hasattr(subclass, "learn_from") and
            callable(subclass.learn_from) or
            NotImplemented
        )

    @abc.abstractmethod
    async def get_model(self, user_id: int) -> ParrotMarkov:
        """ Get a Markov model by user ID. """
        raise NotImplementedError

    @abc.abstractmethod
    async def validate_message(self, message: Message) -> bool:
        """
        A message must pass all of these checks before Parrot can learn from it.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def learn_from(self, message: Message) -> int:
        """ Add a message to a user's corpus. """
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def redis(self) -> Redis: ...

    @property
    @abc.abstractmethod
    def http_session(self) -> aiohttp.ClientSession: ...

    @property
    @abc.abstractmethod
    def registered_users(self) -> RedisSet: ...

    @property
    @abc.abstractmethod
    def learning_channels(self) -> RedisSet: ...

    @property
    @abc.abstractmethod
    def speaking_channels(self) -> RedisSet: ...

    @property
    @abc.abstractmethod
    def corpora(self) -> CorpusManager: ...

    @property
    @abc.abstractmethod
    def avatars(self) -> AvatarManager: ...
