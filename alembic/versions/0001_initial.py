"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-23

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("place_id", sa.String(), nullable=False),
        sa.Column("place_name", sa.String(), nullable=False),
        sa.Column("place_city", sa.String(), nullable=False),
        sa.Column("place_address", sa.String(), nullable=False),
        sa.Column("seats_pattern", sa.String(), nullable=True),
        sa.Column("event_time", sa.DateTime(), nullable=False),
        sa.Column("registration_deadline", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("number_of_visitors", sa.Integer(), nullable=False),
        sa.Column("changed_at", sa.DateTime(), nullable=True),
        sa.Column("synced_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_events_event_time", "events", ["event_time"])

    op.create_table(
        "tickets",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("seat", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("is_cancelled", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tickets_event_id", "tickets", ["event_id"])

    op.create_table(
        "sync_metadata",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("sync_metadata")
    op.drop_index("ix_tickets_event_id", table_name="tickets")
    op.drop_table("tickets")
    op.drop_index("idx_events_event_time", table_name="events")
    op.drop_table("events")
