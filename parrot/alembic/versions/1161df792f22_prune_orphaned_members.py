"""prune orphaned members

Deletes members found not to belong to any guild in 79a4371fbc92.

WARNING!!! This migration is irreversible. You should have a backup of your
database before running migrations anyway but just saying

Revision ID: 1161df792f22
Revises: b8f950e3fb56
Create Date: 2025-02-01 21:58:05.406060

"""

import logging
from collections.abc import Sequence

import sqlmodel as sm
from parrot.alembic.common import cleanup_models, count

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "1161df792f22"
down_revision: str | None = "b8f950e3fb56"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	from parrot.alembic.models import r79a4371fbc92

	session = sm.Session(op.get_bind())
	logging.info(
		f"Initial member count: {count(session, r79a4371fbc92.Member.id)}"
	)
	session.execute(
		sm.text("""
			DELETE FROM member
			WHERE (
				SELECT COUNT(memberguildlink.member_id)
				FROM memberguildlink
				WHERE member_id = member.id
			) == 0
		""")
	)
	logging.info(f"New member count: {count(session, r79a4371fbc92.Member.id)}")
	session.commit()
	cleanup_models(r79a4371fbc92)


def downgrade() -> None:
	logging.warning("No action taken: this migration is irreversible.")
