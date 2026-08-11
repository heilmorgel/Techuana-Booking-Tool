"""Add group_leader, travel_document, home_country

Revision ID: 012_gaesteblatt_fields
Revises: 011_invoice_custom_lines
Create Date: 2026-08-11
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012_gaesteblatt_fields"
down_revision: Union[str, None] = "011_invoice_custom_lines"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("bookings") as batch:
        batch.add_column(sa.Column("group_leader", sa.Text(), nullable=False, server_default=""))
    with op.batch_alter_table("persons") as batch:
        batch.add_column(
            sa.Column("travel_document", sa.String(length=500), nullable=False, server_default="")
        )
    with op.batch_alter_table("operator_settings") as batch:
        batch.add_column(
            sa.Column("home_country", sa.String(length=2), nullable=False, server_default="AT")
        )


def downgrade() -> None:
    with op.batch_alter_table("operator_settings") as batch:
        batch.drop_column("home_country")
    with op.batch_alter_table("persons") as batch:
        batch.drop_column("travel_document")
    with op.batch_alter_table("bookings") as batch:
        batch.drop_column("group_leader")
