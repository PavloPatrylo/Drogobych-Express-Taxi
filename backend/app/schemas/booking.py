from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class BookingCreate(BaseModel):
    trip_id: int
    telegram_id: int
    requested_seats: int = 1
    payment_method: Optional[str] = "CASH"

# === НОВА СХЕМА ДЛЯ ПЕРЕГЛЯДУ КВИТКІВ (UC-P4) ===
class BookingRead(BaseModel):
    id: int
    status: str
    passengers_count: int
    amount_paid: float
    payment_method: str = "CASH"
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
    payment_method: str = "CASH"
    booking_type: str  # ДОДАНО: SEATED, STANDING або PARCEL

class TripManifest(BaseModel):
    trip_id: int
    departure_time: datetime
    from_location: str
    to_location: str
    available_seats: int
    trip_status: str   # ДОДАНО: SCHEDULED, BOARDING, ACTIVE
    passengers: List[PassengerInfo]

class TripStatusUpdate(BaseModel):
    status: str

# Якщо цієї схеми ще немає у файлі, додай її:
class BookingStatusUpdate(BaseModel):
    status: str

class StandingBookingCreate(BaseModel):
    trip_id: int
    telegram_id: int


class ParcelBookingCreate(BaseModel):
    trip_id: int
    telegram_id: int
    description: str = "Посилка"
    price: float = 0.0