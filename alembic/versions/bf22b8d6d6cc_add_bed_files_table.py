"""add bed_files table

Revision ID: bf22b8d6d6cc
Revises: 0df917475eaf
Create Date: 2025-10-03 14:59:27.253115

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bf22b8d6d6cc'
down_revision: Union[str, None] = '0df917475eaf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    query = """
        CREATE TABLE `bed_files` (
        `id` int NOT NULL AUTO_INCREMENT,
        `user` varchar(50) NOT NULL,
        `dataset_name` varchar(255) NOT NULL,
        `filename` varchar(255) NOT NULL,
        `s3_path` varchar(500) NOT NULL,
        `uploaded_at` datetime NOT NULL,
        PRIMARY KEY (`id`),
        UNIQUE KEY `uq_bed_files_user_dataset` (`user`, `dataset_name`),
        KEY `idx_bed_files_user_uploaded` (`user`, `uploaded_at`)
        )
        """
    op.execute(query)


def downgrade() -> None:
    op.execute("DROP TABLE bed_files")
