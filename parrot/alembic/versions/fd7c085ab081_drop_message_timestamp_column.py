"""drop message timestamp column

Revision ID: fd7c085ab081
Revises: e94b76519be5
Create Date: 2024-12-20 15:52:45.701284

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "fd7c085ab081"
down_revision: str | None = "e94b76519be5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	op.drop_column("message", "timestamp")


def downgrade() -> None:
	op.add_column(
		"message",
		sa.Column(
			"timestamp",
			sa.BigInteger(),
			nullable=False,
			server_default="0",
		),
	)
