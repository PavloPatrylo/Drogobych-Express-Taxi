"""add_payment_method_to_bookings

Revision ID: db0be8345da8
Revises: 2dffaf6abc17
Create Date: 2026-08-14 11:22:58.439435

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'db0be8345da8'
down_revision: Union[str, Sequence[str], None] = '2dffaf6abc17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


payment_method_enum = sa.Enum('CASH', 'CARD', name='paymentmethod')

def upgrade() -> None:
    """Upgrade schema."""
    payment_method_enum.create(op.get_bind(), checkfirst=True)
    op.add_column('bookings', sa.Column('payment_method', payment_method_enum, server_default='CASH', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('bookings', 'payment_method')
    payment_method_enum.drop(op.get_bind(), checkfirst=True)
