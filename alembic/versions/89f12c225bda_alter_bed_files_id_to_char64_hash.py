"""alter bed_files id to char64 hash

Revision ID: 89f12c225bda
Revises: bf22b8d6d6cc
Create Date: 2025-10-08 11:50:29.528608

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '89f12c225bda'
down_revision: Union[str, None] = 'bf22b8d6d6cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Remove foreign key constraint from workflow_jobs if it exists
    # This allows workflow_jobs to reference both GWAS datasets and BED files
    from sqlalchemy import text
    conn = op.get_bind()

    # Check if constraint exists
    result = conn.execute(text("""
        SELECT COUNT(*) as cnt FROM information_schema.TABLE_CONSTRAINTS
        WHERE CONSTRAINT_SCHEMA = DATABASE()
        AND TABLE_NAME = 'workflow_jobs'
        AND CONSTRAINT_NAME = 'fk_workflow_jobs_dataset'
        AND CONSTRAINT_TYPE = 'FOREIGN KEY'
    """))
    fk_exists = result.scalar() > 0

    # Drop it if it exists
    if fk_exists:
        op.execute("""
            ALTER TABLE workflow_jobs
            DROP FOREIGN KEY fk_workflow_jobs_dataset
        """)

    # Step 2: Add a temporary column to store the new hash IDs
    op.execute("""
        ALTER TABLE bed_files
        ADD COLUMN new_id char(64) NULL AFTER id
    """)

    # Step 3: Generate hash IDs for existing BED files using SHA256(bed:{dataset_name}-{user})
    # This matches the logic in database_utils.get_dataset_hash(dataset_name, username, prefix="bed:")
    op.execute("""
        UPDATE bed_files
        SET new_id = SHA2(CONCAT('bed:', dataset_name, '-', user), 256)
    """)

    # Step 4: Update any existing workflow_jobs that reference BED files (if any)
    # Match by user and look for jobs that might be BED-related
    # This is a best-effort migration - assumes annot-sldsc method indicates BED files
    op.execute("""
        UPDATE workflow_jobs wj
        INNER JOIN bed_files bf ON wj.user = bf.user
        SET wj.id = bf.new_id
        WHERE wj.method = 'annot-sldsc'
        AND wj.id NOT IN (SELECT id FROM datasets)
    """)

    # Step 5: Drop the old id column and rename new_id to id
    op.execute("""
        ALTER TABLE bed_files
        DROP PRIMARY KEY,
        DROP COLUMN id,
        CHANGE COLUMN new_id id char(64) NOT NULL,
        ADD PRIMARY KEY (id)
    """)


def downgrade() -> None:
    # WARNING: This downgrade is destructive and may lose data
    # It's only safe if no BED files exist or you're okay losing the hash mapping

    # Step 1: Add back auto-increment id column
    op.execute("""
        ALTER TABLE bed_files
        DROP PRIMARY KEY,
        MODIFY COLUMN id int NOT NULL AUTO_INCREMENT,
        ADD PRIMARY KEY (id)
    """)

    # Step 2: Re-add the foreign key constraint to workflow_jobs
    op.execute("""
        ALTER TABLE workflow_jobs
        ADD CONSTRAINT fk_workflow_jobs_dataset
        FOREIGN KEY (id) REFERENCES datasets(id) ON DELETE CASCADE
    """)
