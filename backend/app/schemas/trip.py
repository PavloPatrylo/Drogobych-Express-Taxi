from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# Схема для локації (міста)
class LocationRead(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

# Схема для рейсу, яку ми віддаємо пасажиру
class TripReadPassenger(BaseModel):
    id: int
    from_location: LocationRead
    to_location: LocationRead
    departure_time: datetime
    price_seated: float
    # Цього поля немає в базі, ми його обчислюємо на льоту (seats_available)
    available_seats: int 
    status: str

    class Config:
        from_attributes = True