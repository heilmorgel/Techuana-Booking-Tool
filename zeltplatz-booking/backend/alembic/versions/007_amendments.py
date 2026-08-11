"""Pitch/service date segments and booking amendments

Revision ID: 007_amendments
Revises: 006_person_dates
Create Date: 2026-08-08
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_amendments"
down_revision: Union[str, None] = "006_person_dates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("booking_pitches", "booking_pitches_old")
    op.create_table(
        "booking_pitches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("pitch_id", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pitch_id"], ["pitches.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        INSERT INTO booking_pitches (booking_id, pitch_id, start_date, end_date)
        SELECT bp.booking_id, bp.pitch_id, b.start_date, b.end_date
        FROM booking_pitches_old bp
        JOIN bookings b ON b.id = bp.booking_id
        """
    )
    op.drop_table("booking_pitches_old")

    op.add_column(
        "booking_services",
        sa.Column("start_date", sa.Date(), nullable=False, server_default="1970-01-01"),
    )
    op.add_column(
        "booking_services",
        sa.Column("end_date", sa.Date(), nullable=False, server_default="1970-01-02"),
    )
    op.execute(
        """
        UPDATE booking_services
        SET start_date = (
            SELECT bookings.start_date FROM bookings
            WHERE bookings.id = booking_services.booking_id
        ),
        end_date = (
            SELECT bookings.end_date FROM bookings
            WHERE bookings.id = booking_services.booking_id
        )
        """
    )

    op.create_table(
        "booking_amendments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("diff_json", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("booking_amendments")
    op.drop_column("booking_services", "end_date")
    op.drop_column("booking_services", "start_date")
    op.rename_table("booking_pitches", "booking_pitches_new")
    op.create_table(
        "booking_pitches",
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("pitch_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pitch_id"], ["pitches.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("booking_id", "pitch_id"),
    )
    op.execute(
        """
        INSERT OR IGNORE INTO booking_pitches (booking_id, pitch_id)
        SELECT DISTINCT booking_id, pitch_id FROM booking_pitches_new
        """
    )
    op.drop_table("booking_pitches_new")
