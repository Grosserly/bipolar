"""add user wants random wawa

Revision ID: 2e2045b63d7a
Revises: 6fe6f57202e8
Create Date: 2025-01-21 14:35:35.924268

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "2e2045b63d7a"
down_revision: str | None = "6fe6f57202e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	op.add_column(
		"user",
		sa.Column(
			"wants_random_wawa",
			sa.Boolean(),
			server_default="1",
			nullable=False,
		),
	)


def downgrade() -> None:
	op.drop_column("user", "wants_random_wawa")
