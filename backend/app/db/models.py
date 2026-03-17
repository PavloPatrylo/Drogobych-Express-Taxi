import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Enum, ForeignKey, 
    Index, Integer, Numeric, String, Text, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

class Base(DeclarativeBase):
    pass

# Створюємо перелік (Enum) для ролей
class UserRole(str, enum.Enum):
    PASSENGER = "passenger"
    DRIVER = "driver"
    DISPATCHER = "dispatcher"

class User(Base):
    __tablename__ = "users"

    # Додаємо класичний ID як первинний ключ
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # telegram_id тепер nullable=True, бо диспетчер створює водія до того, як той зайде в бот
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, unique=True, nullable=True, index=True)
    
    # Телефон стає унікальним індексом. Це наш головний "міст" для авторизації
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True, index=True)
    
    full_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Роль користувача (за замовчуванням всі - пасажири)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.PASSENGER)
    
    # Поле для пароля (зберігатимемо хеш або просто текст для початку)
    password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # URL аватарки з Telegram для жовтого Mini App
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Зв'язок зі статистикою
    stats: Mapped["UserStats"] = relationship(back_populates="user", cascade="all, delete-orphan")

class UserStats(Base):
    __tablename__ = "user_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    
    total_trips: Mapped[int] = mapped_column(Integer, default=0)
    total_noshows: Mapped[int] = mapped_column(Integer, default=0)
    trust_score_cached: Mapped[int] = mapped_column(Integer, default=100)

    user: Mapped["User"] = relationship(back_populates="stats")

class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    plate_number: Mapped[str] = mapped_column(String(20), unique=True)
    model: Mapped[str] = mapped_column(String(100))
    total_seats: Mapped[int] = mapped_column(Integer)
    total_standing: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)

class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(primary_key=True)
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
    
    from_location: Mapped["Location"] = relationship("Location", foreign_keys=[from_location_id])
    to_location: Mapped["Location"] = relationship("Location", foreign_keys=[to_location_id])

    __table_args__ = (
        Index("ix_trips_search", "from_location_id", "to_location_id", "departure_time"),
    )

class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"))
    passenger_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    validated_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    booking_type: Mapped[BookingType] = mapped_column(Enum(BookingType))
    source: Mapped[BookingSource] = mapped_column(Enum(BookingSource))
    status: Mapped[BookingStatus] = mapped_column(Enum(BookingStatus), default=BookingStatus.RESERVED)
    
    passengers_count: Mapped[int] = mapped_column(Integer, default=1)
    amount_paid: Mapped[float] = mapped_column(Numeric(10, 2))
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_bookings_trip_status", "trip_id", "status"),
    )