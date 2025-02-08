"""extract avatar info to separate table

Forgets old avatar info; Parrot can regenerate it.

This will make Parrot forget about everything it's left in its avatar store
channel, so you can/should prune it.

Revision ID: 6fe6f57202e8
Revises: fd7c085ab081
Create Date: 2025-01-20 22:15:48.664281

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "6fe6f57202e8"
down_revision: str | None = "fd7c085ab081"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	op.create_table(
		"antiavatar",
		sa.Column("original_url", sa.String(), nullable=False),
		sa.Column("url", sa.String(), nullable=False),
		sa.Column("message_id", sa.BigInteger(), nullable=False),
		sa.Column("user_id", sa.BigInteger(), nullable=False),
		sa.Column("guild_id", sa.BigInteger(), nullable=False),
		sa.ForeignKeyConstraint(["guild_id"], ["guild.id"]),
		sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
		sa.PrimaryKeyConstraint("user_id", "guild_id"),
	)
	op.drop_column("user", "modified_avatar_url")
	op.drop_column("user", "modified_avatar_message_id")
	op.drop_column("user", "original_avatar_url")


def downgrade() -> None:
	op.add_column(
		"user", sa.Column("original_avatar_url", sa.String(), nullable=True)
	)
	op.add_column(
		"user",
		sa.Column("modified_avatar_message_id", sa.BigInteger(), nullable=True),
	)
	op.add_column(
		"user", sa.Column("modified_avatar_url", sa.String(), nullable=True)
	)
	op.drop_table("antiavatar")
