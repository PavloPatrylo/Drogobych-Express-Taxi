import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Enum, ForeignKey, 
    Index, Integer, Numeric, String, Text, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class TripStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    BOARDING = "BOARDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"

class BookingType(str, enum.Enum):
    SEATED = "SEATED"
    STANDING = "STANDING"
    PARCEL = "PARCEL"

class BookingSource(str, enum.Enum):
    BOT = "BOT"
    WEB = "WEB"
    PHONE = "PHONE"
    INSTAGRAM = "INSTAGRAM"
    DRIVER = "DRIVER"

class BookingStatus(str, enum.Enum):
    RESERVED = "RESERVED"
    PAID = "PAID"
    BOARDED = "BOARDED"
    CANCELLED = "CANCELLED"
    NOSHOW = "NOSHOW"
    WAITLIST = "WAITLIST"  # <--- ДОДАНО ДЛЯ СПИСКУ ОЧІКУВАННЯ

class PaymentMethod(str, enum.Enum):
    CASH = "CASH"
    CARD = "CARD"

# Створюємо перелік (Enum) для ролей
class UserRole(str, enum.Enum):
    PASSENGER = "passenger"
    DRIVER = "driver"
    DISPATCHER = "dispatcher"
    ADMIN = "admin"  # <--- ДОДАНО РОЛЬ ВЛАСНИКА

# Типи днів для шаблонів розкладу
class DayType(str, enum.Enum):
    WEEKDAY = "weekday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, unique=True, nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.PASSENGER)
    password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # <--- ДОДАНО ДЛЯ БЛОКУВАННЯ В CRM
    is_active: Mapped[bool] = mapped_column(Boolean, default=True) 
    is_driver_activated: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true") 

    stats: Mapped["UserStats"] = relationship(back_populates="user", cascade="all, delete-orphan")

class UserStats(Base):
    __tablename__ = "user_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    
    total_trips: Mapped[int] = mapped_column(Integer, default=0)
    total_noshows: Mapped[int] = mapped_column(Integer, default=0)
    trust_score_cached: Mapped[int] = mapped_column(Integer, default=100)
    last_trip_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="stats")

class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plate_number: Mapped[str] = mapped_column(String(20), unique=True)
    model: Mapped[str] = mapped_column(String(100))
    total_seats: Mapped[int] = mapped_column(Integer)
    total_standing: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)

# <--- ГЛОБАЛЬНІ НАЛАШТУВАННЯ ТА ТАРИФИ (ВЛАСНИК)
class SystemConfig(Base):
    __tablename__ = "system_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    price_seated: Mapped[float] = mapped_column(Numeric(10, 2), default=200.00)
    price_standing: Mapped[float] = mapped_column(Numeric(10, 2), default=150.00)
    price_parcel: Mapped[float] = mapped_column(Numeric(10, 2), default=100.00)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

# <--- СУТНІСТЬ ДЛЯ ШАБЛОНІВ РОЗКЛАДУ (ВЛАСНИК)
class ScheduleTemplate(Base):
    __tablename__ = "schedule_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day_type: Mapped[DayType] = mapped_column(Enum(DayType))
    
    from_location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    to_location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    
    departure_time: Mapped[str] = mapped_column(String(5)) # формат "HH:MM", напр. "14:30"

    from_location: Mapped["Location"] = relationship("Location", foreign_keys=[from_location_id])
    to_location: Mapped["Location"] = relationship("Location", foreign_keys=[to_location_id])

class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    from_location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    to_location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    
    departure_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    arrival_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    status: Mapped[TripStatus] = mapped_column(Enum(TripStatus), default=TripStatus.SCHEDULED)
    
    seats_limit_snapshot: Mapped[int] = mapped_column(Integer)
    standing_limit_snapshot: Mapped[int] = mapped_column(Integer)
    
    price_seated: Mapped[float] = mapped_column(Numeric(10, 2))
    price_standing: Mapped[float] = mapped_column(Numeric(10, 2))
    price_parcel: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    
    # <--- ДОДАНО ДЛЯ ФІНАНСОВОГО ЗАКРИТТЯ РЕЙСУ
    submitted_amount: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    submitted_cash: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    submitted_card: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    closed_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    close_comment: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    from_location: Mapped["Location"] = relationship("Location", foreign_keys=[from_location_id])
    to_location: Mapped["Location"] = relationship("Location", foreign_keys=[to_location_id])
    vehicle: Mapped["Vehicle"] = relationship("Vehicle")
    driver: Mapped["User"] = relationship("User", foreign_keys=[driver_id])
    closed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[closed_by_id])
    bookings: Mapped[list["Booking"]] = relationship("Booking", back_populates="trip")

    __table_args__ = (
        Index("ix_trips_search", "from_location_id", "to_location_id", "departure_time"),
        Index(
            "uq_trip_driver_slot",
            "driver_id",
            "departure_time",
            unique=True,
            postgresql_where="status != 'CANCELLED'",
        ),
        Index(
            "uq_trip_vehicle_slot",
            "vehicle_id",
            "departure_time",
            unique=True,
            postgresql_where="status != 'CANCELLED'",
        ),
    )

class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"))
    passenger_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    validated_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    booking_type: Mapped[BookingType] = mapped_column(Enum(BookingType))
    source: Mapped[BookingSource] = mapped_column(Enum(BookingSource))
    status: Mapped[BookingStatus] = mapped_column(Enum(BookingStatus), default=BookingStatus.RESERVED)
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), default=PaymentMethod.CASH, server_default="CASH")
    
    passengers_count: Mapped[int] = mapped_column(Integer, default=1)
    amount_paid: Mapped[float] = mapped_column(Numeric(10, 2))
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    trip: Mapped["Trip"] = relationship("Trip", back_populates="bookings")
    passenger: Mapped[Optional["User"]] = relationship("User", foreign_keys=[passenger_id])

    __table_args__ = (
        Index("ix_bookings_trip_status", "trip_id", "status"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    actor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    trip_id: Mapped[Optional[int]] = mapped_column(ForeignKey("trips.id"), nullable=True, index=True)
    passenger_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(30), default="WEB")
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    actor: Mapped[Optional["User"]] = relationship("User", foreign_keys=[actor_id])
    passenger: Mapped[Optional["User"]] = relationship("User", foreign_keys=[passenger_id])
    trip: Mapped[Optional["Trip"]] = relationship("Trip")