"""add_workflow_jobs_table

Revision ID: 0df917475eaf
Revises: 46c6ae70f1b1
Create Date: 2025-09-02 11:15:41.036810

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0df917475eaf'
down_revision: Union[str, None] = '46c6ae70f1b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create new workflow_jobs table (simplified - no workflow column)
    create_table_query = """
        CREATE TABLE `workflow_jobs` (
        `id` char(64) NOT NULL,
        `user` varchar(50) NOT NULL,
        `method` varchar(50) NOT NULL,
        `status` varchar(255) NOT NULL,
        `job_log` longblob NULL,
        `started_at` datetime NOT NULL,
        `updated_at` datetime NOT NULL,
        PRIMARY KEY (`id`, `method`),
        INDEX (`user`),
        INDEX (`status`),
        CONSTRAINT `fk_workflow_jobs_dataset` FOREIGN KEY (`id`) REFERENCES `datasets` (`id`) ON DELETE CASCADE
        )
        """
    op.execute(create_table_query)
    
    # Migrate data from dataset_jobs to workflow_jobs
    # Only migrate jobs where the corresponding dataset still exists
    # Existing jobs will be treated as 'sldsc' since magma is new
    migrate_query = """
        INSERT INTO workflow_jobs (id, user, method, status, job_log, started_at, updated_at)
        SELECT 
            dj.id,
            dj.user,
            'sldsc' as method,
            CASE
                WHEN dj.status LIKE 'RUNNING%' THEN 'RUNNING'
                WHEN dj.status LIKE '%SUCCEEDED%' THEN 'SUCCEEDED'
                WHEN dj.status LIKE '%FAILED%' THEN 'FAILED'
                ELSE dj.status
            END as status,
            dj.job_log,
            dj.updated_at as started_at,
            dj.updated_at
        FROM dataset_jobs dj
        INNER JOIN datasets d ON dj.id = d.id
        WHERE dj.status IS NOT NULL
    """
    op.execute(migrate_query)
    
    # Drop the old dataset_jobs table
    op.execute("DROP TABLE dataset_jobs")


def downgrade() -> None:
    # Recreate dataset_jobs table
    recreate_old_table = """
        CREATE TABLE `dataset_jobs` (
        `id` char(64) NOT NULL,
        `user` varchar(50) NOT NULL,
        `status` varchar(255) NOT NULL,
        `job_log` longblob NULL,
        `updated_at` datetime NOT NULL,
        PRIMARY KEY (`id`)
        )
        """
    op.execute(recreate_old_table)
    
    # Migrate data back (best effort - some information may be lost)
    migrate_back_query = """
        INSERT INTO dataset_jobs (id, user, status, job_log, updated_at)
        SELECT 
            id,
            user,
            CASE 
                WHEN status = 'RUNNING' THEN CONCAT('RUNNING ', method)
                WHEN status = 'SUCCEEDED' THEN CONCAT(method, ' SUCCEEDED')
                WHEN status = 'FAILED' THEN CONCAT(method, ' FAILED')
                ELSE CONCAT(method, ' ', status)
            END as status,
            job_log,
            updated_at
        FROM workflow_jobs
        GROUP BY id, user
        HAVING MAX(updated_at)
    """
    op.execute(migrate_back_query)
    
    # Drop workflow_jobs table
    op.execute("DROP TABLE workflow_jobs")
