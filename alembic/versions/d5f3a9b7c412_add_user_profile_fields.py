"""add user profile fields

Revision ID: d5f3a9b7c412
Revises: c4e2f8a1b305
Create Date: 2026-04-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5f3a9b7c412'
down_revision: Union[str, Sequence[str], None] = 'c4e2f8a1b305'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add profile columns to the user table."""
    op.add_column('user', sa.Column('phone', sa.String(), nullable=True))
    op.add_column('user', sa.Column('bio', sa.String(), nullable=True))
    op.add_column('user', sa.Column('location', sa.String(), nullable=True))
    op.add_column('user', sa.Column('website', sa.String(), nullable=True))
    op.add_column('user', sa.Column('linkedin_url', sa.String(), nullable=True))
    op.add_column('user', sa.Column('github_url', sa.String(), nullable=True))
    op.add_column('user', sa.Column('skills_json', sa.String(), nullable=True))
    op.add_column('user', sa.Column('resume_text', sa.String(), nullable=True))
    op.add_column('user', sa.Column('updated_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove profile columns from the user table."""
    op.drop_column('user', 'updated_at')
    op.drop_column('user', 'resume_text')
    op.drop_column('user', 'skills_json')
    op.drop_column('user', 'github_url')
    op.drop_column('user', 'linkedin_url')
    op.drop_column('user', 'website')
    op.drop_column('user', 'location')
    op.drop_column('user', 'bio')
    op.drop_column('user', 'phone')
