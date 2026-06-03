"""add falcon_tokens

Revision ID: 01e87315f161
Revises: d82261d8b647
Create Date: 2026-05-27 14:52:05.568727

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '01e87315f161'
down_revision: Union[str, None] = 'd82261d8b647'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE falcon_tokens (
            id              INT NOT NULL AUTO_INCREMENT,
            token           CHAR(64) NOT NULL,
            user_id         INT NOT NULL,
            dataset_name    VARCHAR(255) NOT NULL,
            expires_at      TIMESTAMP NOT NULL,
            revoked_at      TIMESTAMP NULL,
            created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY uq_falcon_tokens_token (token),
            KEY ix_falcon_tokens_user_dataset (user_id, dataset_name),
            CONSTRAINT fk_falcon_tokens_user
                FOREIGN KEY (user_id) REFERENCES users(id)
                ON DELETE CASCADE
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE falcon_tokens")
