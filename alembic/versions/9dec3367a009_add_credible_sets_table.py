"""add credible_sets table

Revision ID: 9dec3367a009
Revises: 01e87315f161
Create Date: 2026-09-04 10:05:51.911310

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9dec3367a009'
down_revision: Union[str, None] = '01e87315f161'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Names are compared case-insensitively by MySQL's default collation, so the
    # UNIQUE on (dataset_id, name) already rejects "SuSiE" vs "susie".
    op.execute("""
        CREATE TABLE `credible_sets` (
          `id`          int NOT NULL AUTO_INCREMENT,
          `dataset_id`  char(64)     NOT NULL,
          `user`        varchar(50)  NOT NULL,
          `name`        varchar(30)  NOT NULL,
          `slug`        varchar(30)  NOT NULL,
          `filename`    varchar(255) NOT NULL,
          `separator`   varchar(4)   NOT NULL,
          `col_map`     json         NOT NULL,
          `row_count`   int          NOT NULL,
          `set_count`   int          NOT NULL,
          `uploaded_at` datetime     NOT NULL,
          PRIMARY KEY (`id`),
          UNIQUE KEY `uq_credible_sets_dataset_name` (`dataset_id`, `name`),
          UNIQUE KEY `uq_credible_sets_dataset_slug` (`dataset_id`, `slug`),
          KEY `idx_credible_sets_user` (`user`),
          CONSTRAINT `fk_credible_sets_dataset` FOREIGN KEY (`dataset_id`)
            REFERENCES `datasets` (`id`) ON DELETE CASCADE
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE `credible_sets`")
