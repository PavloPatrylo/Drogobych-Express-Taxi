"""Add location relationships to Trip

Revision ID: b9f48b5111d0
Revises: 9d96b3f09d68
Create Date: 2026-03-17 18:03:12.733645

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9f48b5111d0'
down_revision: Union[str, Sequence[str], None] = '9d96b3f09d68'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'schedule_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('day_type', sa.Enum('WEEKDAY', 'SATURDAY', 'SUNDAY', name='daytype'), nullable=False),
        sa.Column('departure_time', sa.String(length=5), nullable=False),
        sa.Column('route', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_schedule_templates_day_type'), 'schedule_templates', ['day_type'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_schedule_templates_day_type'), table_name='schedule_templates')
    op.drop_table('schedule_templates')
