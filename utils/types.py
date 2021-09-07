import sys

if sys.version_info >= (3, 8):
    from typing import TypedDict  # pylint: disable=no-name-in-module
else:
    from typing_extensions import TypedDict

from typing import Dict, NamedTuple
from discord import User


class ConfirmationBody(NamedTuple):
    author: User  # The forget command message's author
    corpus_owner: User  # User for whose the corpus to be forgotten

# Key: Message ID of a forget command
PendingConfirmations = Dict[int, ConfirmationBody]


class ModifiedAvatar(TypedDict):
    original_avatar_url: str
    modified_avatar_url: str
    source_message_id: int
