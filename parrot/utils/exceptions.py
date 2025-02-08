from typing import Self

from parrot import config
from parrot.utils.types import AnyUser


class _FriendlyError(Exception):
	"""An error we can show directly to the user."""

	def __init__(self, *args: object):
		# Add "Friendly Error: " to the beginning of the error text
		if isinstance(args[0], str) and len(args) >= 2:
			args = ("Friendly Error: " + args[0], *args[1:])
		super().__init__(*args)


class NotRegisteredError(_FriendlyError):
	"""Parrot tried to access data from an unregistered user."""

	@classmethod
	def User(cls, user: AnyUser) -> Self:
		return cls(
			f"User {user.mention} is not opted in to Parrot in this server. "
			f"To opt in, do the `{config.command_prefix}register` command."
		)


class NoDataError(_FriendlyError):
	"""Parrot tried to access an empty or nonexistent corpus."""


class TextNotFoundError(_FriendlyError):
	"""Parrot failed to find text to use for a command."""


class UserNotFoundError(_FriendlyError):
	"""Parrot tried to get a Discord user who does not exist."""

	@classmethod
	def Username(cls, username: str) -> Self:
		return cls(f'User "{username}" does not exist.')


class FeatureDisabledError(_FriendlyError):
	"""A user tried to use a feature that is disabled on this instance of Parrot."""


class UserPermissionError(_FriendlyError):
	"""
	A user tried to commit an action with Parrot that they don't have the right
	permissions to do.
	"""


class AlreadyScanning(_FriendlyError):
	"""
	A user tried to run Quickstart in a channel that Quickstart is already
	scanning for them.
	"""


class ChannelTypeError(_FriendlyError):
	"""
	Requested command is not available in this type of channel.
	"""
