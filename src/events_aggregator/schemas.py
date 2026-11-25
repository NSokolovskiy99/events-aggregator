from datetime import datetime

from pydantic import BaseModel, Field


class PlaceResponse(BaseModel):
    id: str
    name: str
    city: str
    address: str
    seats_pattern: str | None = None


class EventListItem(BaseModel):
    id: str
    name: str
    place: PlaceResponse
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int


class EventListResponse(BaseModel):
    count: int
    next: str | None = None
    previous: str | None = None
    results: list[EventListItem]


class SeatsResponse(BaseModel):
    event_id: str
    available_seats: list[str]


class TicketCreateRequest(BaseModel):
    event_id: str = Field(
        min_length=1, examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    first_name: str = Field(min_length=1, max_length=100, examples=["Иван"])
    last_name: str = Field(min_length=1, max_length=100, examples=["Иванов"])
    # Явный пример нужен, чтобы Swagger UI не генерировал случайную строку
    # из regex-паттерна (иначе в поле подставляется мусор).
    email: str = Field(
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        examples=["ivan@example.com"],
    )
    seat: str = Field(min_length=1, max_length=20, examples=["A15"])


class TicketResponse(BaseModel):
    ticket_id: str


class CancelResponse(BaseModel):
    success: bool
