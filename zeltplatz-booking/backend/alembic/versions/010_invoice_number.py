"""Add unique invoice_number to bookings

Revision ID: 010_invoice_number
Revises: 009_price_profiles
Create Date: 2026-08-11
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_invoice_number"
down_revision: Union[str, None] = "009_price_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("bookings") as batch:
        batch.add_column(sa.Column("invoice_number", sa.String(length=32), nullable=True))
        batch.create_unique_constraint("uq_bookings_invoice_number", ["invoice_number"])


def downgrade() -> None:
    with op.batch_alter_table("bookings") as batch:
        batch.drop_constraint("uq_bookings_invoice_number", type_="unique")
        batch.drop_column("invoice_number")
