"""add cascade delete relationships

Revision ID: b8f950e3fb56
Revises: 79a4371fbc92
Create Date: 2025-01-21 14:46:13.725138

"""

import logging
from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b8f950e3fb56"
down_revision: str | None = "79a4371fbc92"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	with op.batch_alter_table("membership") as batch_op:
		batch_op.drop_constraint(
			op.f("fk_membership_member_id_member"), type_="foreignkey"
		)
		batch_op.create_foreign_key(
			None, "user", ["member_id"], ["id"], ondelete="CASCADE"
		)
	try:
		with op.batch_alter_table("message") as batch_op:
			batch_op.drop_constraint(
				op.f("fk_messages_user_id_users"), type_="foreignkey"
			)
	except ValueError as exc:
		logging.warning(exc)
	with op.batch_alter_table("message") as batch_op:
		batch_op.create_foreign_key(
			None, "user", ["author_id"], ["id"], ondelete="CASCADE"
		)
	with op.batch_alter_table("antiavatar") as batch_op:
		batch_op.drop_constraint(
			op.f("fk_antiavatar_member_id_member"), type_="foreignkey"
		)
		batch_op.create_foreign_key(
			None, "user", ["member_id"], ["id"], ondelete="CASCADE"
		)


def downgrade() -> None:
	with op.batch_alter_table("membership") as batch_op:
		batch_op.drop_constraint(
			op.f("fk_membership_member_id_member"), type_="foreignkey"
		)
		batch_op.create_foreign_key(
			None, "user", ["member_id"], ["id"], ondelete=None
		)
	with op.batch_alter_table("message") as batch_op:
		batch_op.drop_constraint(
			op.f("fk_message_author_id_member"), type_="foreignkey"
		)
		batch_op.create_foreign_key(
			op.f("fk_messages_user_id_users"),
			"user",
			["author_id"],
			["id"],
			ondelete=None,
		)
	with op.batch_alter_table("antiavatar") as batch_op:
		batch_op.drop_constraint(
			op.f("fk_antiavatar_member_id_member"), type_="foreignkey"
		)
		batch_op.create_foreign_key(
			None, "user", ["member_id"], ["id"], ondelete=None
		)
