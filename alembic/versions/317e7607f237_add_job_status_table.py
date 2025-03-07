"""add job status table

Revision ID: 317e7607f237
Revises: a404fa653076
Create Date: 2025-02-22 16:40:14.683634

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '317e7607f237'
down_revision: Union[str, None] = 'a404fa653076'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    query = """
        CREATE TABLE `dataset_jobs` (
        `id` char(64) NOT NULL,
        `user` varchar(50) NOT NULL,
        `status` varchar(255) NOT NULL,
        `job_log` longblob NULL,
        `updated_at` datetime NOT NULL,
        PRIMARY KEY (`id`)
        )
        """
    op.execute(query)


def downgrade() -> None:
    op.execute("drop table dataset_jobs")
