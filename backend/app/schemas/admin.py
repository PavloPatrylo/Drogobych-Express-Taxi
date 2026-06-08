from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from .user import UserRead
from .trip import LocationRead

class VehicleBase(BaseModel):
    plate_number: str
    model: str
    total_seats: int
    total_standing: int
    is_active: bool = True

class VehicleCreate(VehicleBase):
    pass

class VehicleRead(VehicleBase):
    id: int
    class Config:
        from_attributes = True

class TripCreate(BaseModel):
    driver_id: int
    vehicle_id: int
    from_location_id: int
    to_location_id: int
    departure_time: datetime
    price_seated: float
    price_standing: float

class TripAdminRead(BaseModel):
    id: int
    driver: UserRead
    vehicle: VehicleRead
    from_location: LocationRead
    to_location: LocationRead
    departure_time: datetime
    arrival_time: Optional[datetime]
    status: str
    seats_limit_snapshot: int
    standing_limit_snapshot: int
    price_seated: float
    price_standing: float
    
    class Config:
        from_attributes = True

class AdminStats(BaseModel):
    users_total: int
    trips_total: int
    bookings_total: int
    revenue_today: float
