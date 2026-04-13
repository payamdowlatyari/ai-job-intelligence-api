"""change job id to uuid

Revision ID: b3f1a7e2d901
Revises: 5ca8d0c895c4
Create Date: 2026-04-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3f1a7e2d901'
down_revision: Union[str, Sequence[str], None] = '5ca8d0c895c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Change job.id from auto-increment integer to UUID string."""
    # Add a temporary UUID column
    op.add_column('job', sa.Column('new_id', sa.String(), nullable=True))

    # Populate it with UUIDs for existing rows
    op.execute(
        "UPDATE job SET new_id = gen_random_uuid()::text"
    )

    # Make it non-nullable
    op.alter_column('job', 'new_id', nullable=False)

    # Drop the old PK and column, rename new column
    op.drop_constraint('job_pkey', 'job', type_='primary')
    op.drop_column('job', 'id')
    op.alter_column('job', 'new_id', new_column_name='id')
    op.create_primary_key('job_pkey', 'job', ['id'])


def downgrade() -> None:
    """Revert job.id back to auto-increment integer."""
    op.drop_constraint('job_pkey', 'job', type_='primary')
    op.drop_column('job', 'id')
    op.add_column('job', sa.Column('id', sa.Integer(), autoincrement=True, nullable=False))
    op.create_primary_key('job_pkey', 'job', ['id'])
