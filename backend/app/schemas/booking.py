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

from typing import List

# === СХЕМИ ДЛЯ ВОДІЯ (UC-D1) ===
class PassengerInfo(BaseModel):
    booking_id: int
    full_name: str
    phone: str
    seats: int
    status: str
    amount_paid: float

class TripManifest(BaseModel):
    trip_id: int
    departure_time: datetime
    from_location: str
    to_location: str
    available_seats: int
    passengers: List[PassengerInfo]