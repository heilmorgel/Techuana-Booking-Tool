"""Add pitch daily_price and person fee tables

Revision ID: 005_billing
Revises: 004_booking_notes
Create Date: 2026-08-08
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_billing"
down_revision: Union[str, None] = "004_booking_notes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pitches",
        sa.Column("daily_price", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )
    op.create_table(
        "person_fee_elements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("daily_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "person_fee_brackets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("element_id", sa.Integer(), nullable=False),
        sa.Column("age_from", sa.Integer(), nullable=False),
        sa.Column("age_to_exclusive", sa.Integer(), nullable=True),
        sa.Column("daily_price", sa.Numeric(10, 2), nullable=False),
        sa.ForeignKeyConstraint(["element_id"], ["person_fee_elements.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("person_fee_brackets")
    op.drop_table("person_fee_elements")
    op.drop_column("pitches", "daily_price")
