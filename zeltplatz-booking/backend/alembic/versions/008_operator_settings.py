"""Operator / club settings for invoices

Revision ID: 008_operator_settings
Revises: 007_amendments
Create Date: 2026-08-08
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_operator_settings"
down_revision: Union[str, None] = "007_amendments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "operator_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("address", sa.Text(), nullable=False, server_default=""),
        sa.Column("iban", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("logo_filename", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        INSERT INTO operator_settings (id, organization_name, address, iban, logo_filename)
        VALUES (1, '', '', '', NULL)
        """
    )


def downgrade() -> None:
    op.drop_table("operator_settings")
