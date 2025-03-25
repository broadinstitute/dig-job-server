"""add datasets table

Revision ID: 46c6ae70f1b1
Revises: 317e7607f237
Create Date: 2025-03-25 11:31:10.041137

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '46c6ae70f1b1'
down_revision: Union[str, None] = '317e7607f237'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    query = """
        CREATE TABLE `datasets` (
        `id` char(64) NOT NULL,
        `uploaded_by` varchar(50) NOT NULL,
        `metadata` json NOT NULL,
        `uploaded_at` datetime NOT NULL,
        PRIMARY KEY (`id`)
        )
        """
    op.execute(query)



def downgrade() -> None:
    op.execute("drop table datasets")
