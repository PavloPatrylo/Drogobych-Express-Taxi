"""add_audit_logs

Revision ID: 5c8a2c1fd9ab
Revises: 22d0bc20f898
Create Date: 2026-06-21 16:20:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5c8a2c1fd9ab"
down_revision: Union[str, Sequence[str], None] = "22d0bc20f898"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("trip_id", sa.Integer(), nullable=True),
        sa.Column("passenger_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["passenger_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)
    op.create_index("ix_audit_logs_passenger_id", "audit_logs", ["passenger_id"], unique=False)
    op.create_index("ix_audit_logs_trip_id", "audit_logs", ["trip_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_logs_trip_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_passenger_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_table("audit_logs")
