"""edit make registrations many to many

Revision ID: 98da0772ccf1
Revises: 76966ae46b3b
Create Date: 2024-12-24 15:02:57.204982

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "98da0772ccf1"
down_revision: str | None = "76966ae46b3b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	# Drop old column on the User table
	op.drop_column("User", "is_registered")

	# Create the new table
	op.create_table(
		"Registration",
		sa.Column("id", sa.BigInteger, primary_key=True),
		sa.Column("guild_id", sa.BigInteger, sa.ForeignKey("Guild.id")),
		sa.Column("user_id", sa.BigInteger, sa.ForeignKey("User.id")),
	)


def downgrade() -> None:
	op.drop_table("Registration")
	op.add_column(
		"User", sa.Column("is_registered", sa.Boolean, server_default="false")
	)
