from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class BookingCreate(BaseModel):
    trip_id: int
    telegram_id: int
    requested_seats: int = 1

# === НОВА СХЕМА ДЛЯ ПЕРЕГЛЯДУ КВИТКІВ (UC-P4) ===
class BookingRead(BaseModel):
    id: int
    status: str
    passengers_count: int
    amount_paid: float
    trip_departure_time: datetime
    from_location: str
    to_location: str

    class Config:
        from_attributes = True