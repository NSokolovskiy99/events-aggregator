"""constraints: active seat uniqueness and visitors check

Revision ID: 0002_constraints
Revises: 0001_initial
Create Date: 2026-11-24

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_constraints"
down_revision: str | Sequence[str] | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_check_constraint(
        "ck_events_visitors_non_negative",
        "events",
        "number_of_visitors >= 0",
    )
    # Частичный уникальный индекс: активное место уникально в рамках события.
    op.create_index(
        "uq_tickets_event_seat_active",
        "tickets",
        ["event_id", "seat"],
        unique=True,
        postgresql_where=sa.text("is_cancelled = false"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_tickets_event_seat_active", table_name="tickets")
    op.drop_constraint("ck_events_visitors_non_negative", "events", type_="check")
