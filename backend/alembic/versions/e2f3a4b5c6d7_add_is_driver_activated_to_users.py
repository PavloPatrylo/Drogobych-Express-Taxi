"""add_is_driver_activated_to_users

Revision ID: e2f3a4b5c6d7
Revises: d033cbb3c465
Create Date: 2026-09-04 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2f3a4b5c6d7'
down_revision: Union[str, Sequence[str], None] = 'd033cbb3c465'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_driver_activated BOOLEAN DEFAULT 'true' NOT NULL;")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'is_driver_activated')
