"""Initial migration

Revision ID: a404fa653076
Revises: 
Create Date: 2024-07-24 12:05:19.754683

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a404fa653076'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    query = """
        CREATE TABLE `users` (
        `id` int NOT NULL AUTO_INCREMENT,
        `user_name` varchar(50) NOT NULL UNIQUE,
        `password` varchar(255),
        `created_at` datetime NOT NULL,
        `last_login` datetime,   
        PRIMARY KEY (`id`)
        )
        """
    op.execute(query)


def downgrade() -> None:
    op.execute("DROP TABLE `users`")
