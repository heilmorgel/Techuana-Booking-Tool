"""Add person start/end dates

Revision ID: 006_person_dates
Revises: 005_billing
Create Date: 2026-08-08
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_person_dates"
down_revision: Union[str, None] = "005_billing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "persons",
        sa.Column("start_date", sa.Date(), nullable=False, server_default="1970-01-01"),
    )
    op.add_column(
        "persons",
        sa.Column("end_date", sa.Date(), nullable=False, server_default="1970-01-02"),
    )
    op.execute(
        """
        UPDATE persons
        SET start_date = (
            SELECT bookings.start_date FROM bookings WHERE bookings.id = persons.booking_id
        ),
        end_date = (
            SELECT bookings.end_date FROM bookings WHERE bookings.id = persons.booking_id
        )
        """
    )


def downgrade() -> None:
    op.drop_column("persons", "end_date")
    op.drop_column("persons", "start_date")
