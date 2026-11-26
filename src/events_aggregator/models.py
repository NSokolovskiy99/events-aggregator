import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from events_aggregator.database import Model
from events_aggregator.enums import EventStatus
from events_aggregator.timeutils import db_now


class Event(Model):
    __tablename__ = "events"
    __table_args__ = (
        Index("idx_events_event_time", "event_time"),
        CheckConstraint(
            "number_of_visitors >= 0", name="ck_events_visitors_non_negative"
        ),
    )

    id: Mapped[str] = mapped_column(primary_key=True)  # UUID от Events Provider
    name: Mapped[str] = mapped_column(String(255))
    place_id: Mapped[str] = mapped_column(String)
    place_name: Mapped[str] = mapped_column(String)
    place_city: Mapped[str] = mapped_column(String)
    place_address: Mapped[str] = mapped_column(String)
    seats_pattern: Mapped[str | None] = mapped_column(String)  # например "A1-100,B1-50"
    event_time: Mapped[datetime] = mapped_column(DateTime)
    registration_deadline: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[EventStatus] = mapped_column(String)
    number_of_visitors: Mapped[int] = mapped_column(default=0)
    changed_at: Mapped[datetime | None] = mapped_column(DateTime)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=db_now)

    tickets = relationship("Ticket", back_populates="event")


class Ticket(Model):
    __tablename__ = "tickets"
    # Активное (не отменённое) место уникально в рамках события —
    # защита от двойного бронирования на уровне БД.
    __table_args__ = (
        Index(
            "uq_tickets_event_seat_active",
            "event_id",
            "seat",
            unique=True,
            postgresql_where=text("is_cancelled = false"),
        ),
    )

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    seat: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=db_now)
    is_cancelled: Mapped[bool] = mapped_column(default=False)

    event: Mapped[Event] = relationship(back_populates="tickets")


class SyncMetadata(Model):
    __tablename__ = "sync_metadata"

    key: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[str] = mapped_column(String)
