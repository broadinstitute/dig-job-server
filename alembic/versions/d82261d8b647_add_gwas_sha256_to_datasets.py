"""add gwas_sha256 to datasets

Revision ID: d82261d8b647
Revises: 89f12c225bda
Create Date: 2026-05-20 09:31:26.527551

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd82261d8b647'
down_revision: Union[str, None] = '89f12c225bda'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE datasets
        ADD COLUMN gwas_sha256 CHAR(64) NULL AFTER metadata
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE datasets DROP COLUMN gwas_sha256")
