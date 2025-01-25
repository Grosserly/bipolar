"""add channel webhook id default value

Revision ID: e94b76519be5
Revises: 21069c329505
Create Date: 2025-01-22 23:34:25.443986

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e94b76519be5"
down_revision: str | None = "21069c329505"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	with op.batch_alter_table("channel") as batch_op:
		batch_op.alter_column("webhook_id", server_default=sa.null())


def downgrade() -> None:
	with op.batch_alter_table("channel") as batch_op:
		batch_op.alter_column("webhook_id", server_default=None)
