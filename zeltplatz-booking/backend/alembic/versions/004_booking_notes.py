"""Add notes to bookings

Revision ID: 004_booking_notes
Revises: 003_daily_price
Create Date: 2026-08-07
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_booking_notes"
down_revision: Union[str, None] = "003_daily_price"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bookings",
        sa.Column("notes", sa.String(length=2000), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("bookings", "notes")
