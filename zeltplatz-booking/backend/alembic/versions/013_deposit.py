"""Add deposit fields and booking deposit_paid_at

Revision ID: 013_deposit
Revises: 012_gaesteblatt_fields
Create Date: 2026-08-12
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013_deposit"
down_revision: Union[str, None] = "012_gaesteblatt_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("pitches") as batch:
        batch.add_column(
            sa.Column("deposit", sa.Numeric(10, 2), nullable=False, server_default="0")
        )
    with op.batch_alter_table("services") as batch:
        batch.add_column(
            sa.Column("deposit", sa.Numeric(10, 2), nullable=False, server_default="0")
        )
    with op.batch_alter_table("price_profiles") as batch:
        batch.add_column(
            sa.Column("deposit", sa.Numeric(10, 2), nullable=False, server_default="0")
        )
    with op.batch_alter_table("bookings") as batch:
        batch.add_column(sa.Column("deposit_paid_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("bookings") as batch:
        batch.drop_column("deposit_paid_at")
    with op.batch_alter_table("price_profiles") as batch:
        batch.drop_column("deposit")
    with op.batch_alter_table("services") as batch:
        batch.drop_column("deposit")
    with op.batch_alter_table("pitches") as batch:
        batch.drop_column("deposit")
