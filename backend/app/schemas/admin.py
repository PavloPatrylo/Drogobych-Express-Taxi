from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator
from typing import Optional, List
from datetime import datetime
from app.db.models import TripStatus, BookingStatus, BookingSource, BookingType, DayType, UserRole, PaymentMethod

# ══════════════════════════════════════════════
# СХЕМИ ДЛЯ АВТОПАРКУ (VEHICLES)
# ══════════════════════════════════════════════
class VehicleBase(BaseModel):
    plate_number: str
    model: str
    total_seats: int = Field(..., gt=0)
    total_standing: int = Field(..., ge=0)
    is_active: bool = True

class VehicleCreate(VehicleBase):
    pass

class VehicleResponse(VehicleBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class LocationResponse(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)

# ══════════════════════════════════════════════
# СХЕМИ ДЛЯ ПЕРСОНАЛУ ТА КЛІЄНТІВ (USERS)
# ══════════════════════════════════════════════
class UserResponse(BaseModel):
    id: int
    full_name: Optional[str] = None
    phone: Optional[str] = None
    telegram_id: Optional[int] = None
    role: UserRole
    is_active: bool = True
    
    model_config = ConfigDict(from_attributes=True)

# ══════════════════════════════════════════════
# СХЕМИ ДЛЯ ШАБЛОНІВ РОЗКЛАДУ (TEMPLATES)
# ══════════════════════════════════════════════
class ScheduleTemplateBase(BaseModel):
    day_type: DayType
    from_location_id: int
    to_location_id: int
    departure_time: str

class ScheduleTemplateCreate(ScheduleTemplateBase):
    pass

class ScheduleTemplateResponse(ScheduleTemplateBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# ══════════════════════════════════════════════
# СХЕМИ ДЛЯ РЕЙСІВ (TRIPS)
# ══════════════════════════════════════════════
class TripBase(BaseModel):
    driver_id: int
    vehicle_id: int
    from_location_id: int
    to_location_id: int
    departure_time: datetime
    arrival_time: Optional[datetime] = None
    price_seated: float
    price_standing: float
    price_parcel: float = 100.0

class TripCreate(TripBase):
    pass

class TripResponse(TripBase):
    id: int
    status: TripStatus
    seats_limit_snapshot: int
    standing_limit_snapshot: int
    submitted_amount: Optional[float] = None
    closed_by_id: Optional[int] = None
    
    vehicle: Optional[VehicleResponse] = None
    driver: Optional[UserResponse] = None
    
    model_config = ConfigDict(from_attributes=True)

class BookingResponse(BaseModel):
    id: int
    trip_id: int
    passenger_id: Optional[int] = None
    status: BookingStatus
    booking_type: BookingType
    source: BookingSource
    passengers_count: int
    amount_paid: float
    payment_method: PaymentMethod = PaymentMethod.CASH
    passenger_name: Optional[str] = None 
    passenger_phone: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class AdminVehicleResponse(BaseModel):
    id: int
    plate: str
    plate_number: str
    model: str
    total_seats: int
    total_standing: int
    is_active: bool


class AdminUserResponse(BaseModel):
    id: int
    name: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    telegram_id: Optional[int] = None
    role: UserRole
    is_active: bool
    is_driver: bool = False
    total_trips: int = 0
    total_noshows: int = 0
    trust_score: int = 100
    registration_source: Optional[str] = "Telegram-бот"
    last_trip_date: Optional[str] = None
    created_at: Optional[str] = None


class AdminTripResponse(BaseModel):
    id: int
    driver_id: int
    vehicle_id: int
    from_location_id: int
    to_location_id: int
    route: str
    date: str
    departure_time: str
    arrival_time: Optional[str] = None
    status: TripStatus
    seats_limit_snapshot: int
    standing_limit_snapshot: int
    price_seated: float
    price_standing: float
    price_parcel: float = 100.0
    submitted_amount: Optional[float] = None
    submitted_cash: Optional[float] = None
    submitted_card: Optional[float] = None
    closed_by_id: Optional[int] = None
    closed_by: Optional[str] = None
    close_comment: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    vehicle_plate: Optional[str] = None
    vehicle_model: Optional[str] = None
    booked_seats: int = 0
    booked_standing: int = 0
    parcels_count: int = 0
    total_revenue: float = 0.0


class AdminBookingResponse(BaseModel):
    id: int
    trip_id: int
    passenger_id: Optional[int] = None
    created_by_id: int
    booking_type: BookingType
    source: BookingSource
    status: BookingStatus
    passengers_count: int
    amount_paid: float
    payment_method: PaymentMethod = PaymentMethod.CASH
    comment: Optional[str] = None
    created_at: Optional[datetime] = None
    passenger_name: Optional[str] = None
    passenger_phone: Optional[str] = None


class TripManifestDetailResponse(BaseModel):
    trip: AdminTripResponse
    seated_count: int
    seated_limit: int
    standing_count: int
    standing_limit: int
    parcels_count: int
    total_revenue: float
    bookings: List[AdminBookingResponse]


class AdminManifestBookingCreate(BaseModel):
    booking_type: BookingType = BookingType.SEATED
    source: BookingSource = BookingSource.PHONE
    payment_method: PaymentMethod = PaymentMethod.CASH
    phone: str
    full_name: Optional[str] = None
    seats: int = Field(1, gt=0)
    comment: Optional[str] = None


class AdminBookingStatusUpdate(BaseModel):
    status: BookingStatus


class AdminDashboardResponse(BaseModel):
    trips: List[AdminTripResponse]
    bookings: List[AdminBookingResponse]
    passengers: List[AdminUserResponse]
    vehicles: List[AdminVehicleResponse]
    drivers: List[AdminUserResponse]


class SystemConfigResponse(BaseModel):
    id: int = 1
    price_seated: float
    price_standing: float
    price_parcel: float
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class SystemConfigUpdate(BaseModel):
    price_seated: float = Field(..., gt=0)
    price_standing: float = Field(..., gt=0)
    price_parcel: float = Field(..., gt=0)


class AdminTripCreate(BaseModel):
    driver_id: int
    vehicle_id: int
    route: str
    date: str
    departure_time: str
    arrival_time: Optional[str] = None
    price_seated: Optional[float] = None
    price_standing: Optional[float] = None
    price_parcel: Optional[float] = None

    @model_validator(mode="after")
    def departure_must_be_valid(self):
        try:
            datetime.fromisoformat(f"{self.date}T{self.departure_time}")
        except ValueError as exc:
            raise ValueError("date must be YYYY-MM-DD and departure_time must be HH:MM") from exc
        return self


class AdminBatchTripItem(BaseModel):
    driver_id: int
    vehicle_id: int
    route: str
    date: str
    departure_time: str
    arrival_time: Optional[str] = None


class AdminBatchTripCreate(BaseModel):
    trips: List[AdminBatchTripItem]


class AdminTripUpdate(BaseModel):
    driver_id: int
    vehicle_id: int
    route: str
    date: str
    departure_time: str
    arrival_time: Optional[str] = None
    price_seated: float
    price_standing: float
    price_parcel: Optional[float] = None

    @model_validator(mode="after")
    def departure_must_be_valid(self):
        try:
            datetime.fromisoformat(f"{self.date}T{self.departure_time}")
        except ValueError as exc:
            raise ValueError("date must be YYYY-MM-DD and departure_time must be HH:MM") from exc
        return self


class AdminTripStatusUpdate(BaseModel):
    status: TripStatus


class AdminTripAssignUpdate(BaseModel):
    driver_id: Optional[int] = None
    vehicle_id: Optional[int] = None


class AdminCloseTripRequest(BaseModel):
    submitted_cash: Optional[float] = 0.0
    submitted_card: Optional[float] = 0.0
    submitted_amount: Optional[float] = None
    comment: Optional[str] = None


class AdminOfflineBookingCreate(BaseModel):
    trip_id: int
    phone: str
    full_name: Optional[str] = None
    source: BookingSource = BookingSource.PHONE
    payment_method: PaymentMethod = PaymentMethod.CASH
    seats: int = Field(1, gt=0)

    @field_validator("phone")
    def validate_phone_number(cls, v: str) -> str:
        import re
        digits = re.sub(r"\D", "", v or "")
        if digits.startswith("380") and len(digits) == 12:
            digits = digits[2:]
        if len(digits) != 10:
            raise ValueError("Номер телефону повинен містити рівно 10 цифр (наприклад: 0971234567)")
        if not digits.startswith("0"):
            raise ValueError("Номер телефону повинен починатися з 0 (наприклад: 0971234567)")
        return f"+38{digits}"


class BroadcastRequest(BaseModel):
    trip_id: Optional[int] = None
    target_group: Optional[str] = "all"
    text: str = Field(..., min_length=1)


class AdminAuditLogResponse(BaseModel):
    id: int
    created_at: datetime
    time: str
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    trip_id: Optional[int] = None
    passenger_id: Optional[int] = None
    trip: str = "—"
    passenger: str = "—"
    source: str
    by: str = "System"
    message: Optional[str] = None


class StaffCreate(BaseModel):
    full_name: str
    phone: str
    role: UserRole
    password: Optional[str] = None

    @field_validator("phone")
    def validate_phone_number(cls, v: str) -> str:
        import re
        digits = re.sub(r"\D", "", v or "")
        if digits.startswith("380") and len(digits) == 12:
            digits = digits[2:]
        if len(digits) != 10:
            raise ValueError("Номер телефону повинен містити рівно 10 цифр (наприклад: 0971234567)")
        if not digits.startswith("0"):
            raise ValueError("Номер телефону повинен починатися з 0 (наприклад: 0971234567)")
        return f"+38{digits}"


class StaffUpdate(BaseModel):
    full_name: str
    phone: str
    role: UserRole
    password: Optional[str] = None

    @field_validator("phone")
    def validate_phone_number(cls, v: str) -> str:
        import re
        digits = re.sub(r"\D", "", v or "")
        if digits.startswith("380") and len(digits) == 12:
            digits = digits[2:]
        if len(digits) != 10:
            raise ValueError("Номер телефону повинен містити рівно 10 цифр (наприклад: 0971234567)")
        if not digits.startswith("0"):
            raise ValueError("Номер телефону повинен починатися з 0 (наприклад: 0971234567)")
        return f"+38{digits}"


class PublishScheduleRequest(BaseModel):
    date_from: str
    date_to: str
    driver_id: Optional[int] = None
    comment: Optional[str] = None


class PublishSchedulePreviewResponse(BaseModel):
    trips_count: int
    drivers_count: int
    total_seats_limit: int
    total_revenue: float
    date_from: str
    date_to: str


class ConfirmDriverCashRequest(BaseModel):
    driver_id: int
    target_date: str
    received_cash: float = 0.0
    received_card: float = 0.0
    comment: Optional[str] = None


class DriverReportItem(BaseModel):
    driver_id: int
    driver_name: str
    driver_phone: Optional[str] = None
    trips_count: int = 0
    completed_trips_count: int = 0
    total_passengers: int = 0
    cash_revenue: float = 0.0
    card_revenue: float = 0.0
    total_revenue: float = 0.0
    avg_revenue_per_trip: float = 0.0


class VehicleReportItem(BaseModel):
    vehicle_id: int
    plate_number: str
    model: str
    total_seats: int
    total_standing: int
    trips_count: int = 0
    total_passengers: int = 0
    total_seats_capacity: int = 0
    occupancy_rate: float = 0.0
    cash_revenue: float = 0.0
    card_revenue: float = 0.0
    total_revenue: float = 0.0
    avg_revenue_per_trip: float = 0.0
