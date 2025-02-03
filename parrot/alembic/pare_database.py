"""
Take Parrot's real database and remove a certain proportion of its messages.
For testing on a smaller version of the real database.
"""

import logging

import sqlmodel as sm
from parrot import config
from parrot.alembic import prepare_for_migration
from parrot.alembic.models import v1


V1_REVISION = "fe3138aef0bd"

PARING_FACTOR = 2_0000  # 4,000,000 → 200 messages


def main() -> None:
	prepare_for_migration.main()

	engine = sm.create_engine(config.db_url)
	sm.SQLModel.metadata.create_all(engine)
	session = sm.Session(engine)

	logging.info("Paring message table")
	db_messages_count: int = session.execute(
		sm.func.count(v1.Messages.id)  # type: ignore -- it works
	).scalar()
	logging.info(f"Initial message count: {db_messages_count}")
	logging.info(
		f"Estimated new count after paring: {db_messages_count // PARING_FACTOR}"
	)
	session.execute(
		sm.text("""
			DELETE FROM messages WHERE id IN (
				SELECT id
				FROM (
					SELECT id, ROW_NUMBER() OVER () row_num
					FROM messages
				) t
				WHERE MOD(row_num, :factor) != 0
			)
		"""),
		{"factor": PARING_FACTOR},
	)

	db_messages_count: int = session.execute(
		sm.func.count(v1.Messages.id)  # type: ignore
	).scalar()
	logging.info(f"New message count: {db_messages_count}")


if __name__ == "__main__":
	main()
