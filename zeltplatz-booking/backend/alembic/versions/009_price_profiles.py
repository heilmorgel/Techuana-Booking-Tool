"""Add price profiles and scope person fees / persons

Revision ID: 009_price_profiles
Revises: 008_operator_settings
Create Date: 2026-08-11
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_price_profiles"
down_revision: Union[str, None] = "008_operator_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "price_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.execute(
        """
        INSERT INTO price_profiles (name, is_default, sort_order)
        VALUES ('Standard', 1, 0)
        """
    )

    with op.batch_alter_table("person_fee_elements") as batch:
        batch.add_column(sa.Column("price_profile_id", sa.Integer(), nullable=True))

    op.execute(
        """
        UPDATE person_fee_elements
        SET price_profile_id = (SELECT id FROM price_profiles WHERE name = 'Standard' LIMIT 1)
        """
    )

    with op.batch_alter_table("person_fee_elements") as batch:
        batch.alter_column("price_profile_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(
            "fk_person_fee_elements_price_profile_id",
            "price_profiles",
            ["price_profile_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch.drop_constraint("uq_person_fee_elements_name", type_="unique")
        batch.create_unique_constraint(
            "uq_person_fee_element_profile_name",
            ["price_profile_id", "name"],
        )

    with op.batch_alter_table("persons") as batch:
        batch.add_column(sa.Column("price_profile_id", sa.Integer(), nullable=True))

    op.execute(
        """
        UPDATE persons
        SET price_profile_id = (SELECT id FROM price_profiles WHERE is_default = 1 LIMIT 1)
        """
    )

    with op.batch_alter_table("persons") as batch:
        batch.alter_column("price_profile_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(
            "fk_persons_price_profile_id",
            "price_profiles",
            ["price_profile_id"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    with op.batch_alter_table("persons") as batch:
        batch.drop_constraint("fk_persons_price_profile_id", type_="foreignkey")
        batch.drop_column("price_profile_id")

    with op.batch_alter_table("person_fee_elements") as batch:
        batch.drop_constraint("uq_person_fee_element_profile_name", type_="unique")
        batch.drop_constraint("fk_person_fee_elements_price_profile_id", type_="foreignkey")
        batch.drop_column("price_profile_id")
        batch.create_unique_constraint("uq_person_fee_elements_name", ["name"])

    op.drop_table("price_profiles")
