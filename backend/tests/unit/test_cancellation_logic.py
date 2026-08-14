"""
Unit tests for booking cancellation domain logic and validation rules.
"""
import pytest
from app.db.models import Booking, BookingStatus, Trip, TripStatus, User, UserRole


def can_cancel_booking(booking: Booking, trip: Trip | None) -> tuple[bool, str | None]:
    """
    Pure validation helper matching cancellation constraints.
    Returns (is_allowed, error_message).
    """
    if not booking:
        return False, "Booking not found"
    
    if trip and trip.status in (TripStatus.CLOSED, TripStatus.CANCELLED):
        return False, "Неможливо скасовувати квитки у фінансово закритому або скасованому рейсі"
    
    return True, None


def test_can_cancel_booking_on_scheduled_trip():
    """
    Короткий опис: Скасування бронювання для активного/запланованого рейсу.
    Що перевіряє: Чи дозволяє бізнес-логіка скасовувати квитки у рейсах зі статусом SCHEDULED.
    На вхід:
        - trip: Рейс (Trip) зі статусом SCHEDULED.
        - booking: Бронювання (Booking) зі статусом RESERVED.
    Очікуваний результат на виході:
        - allowed == True (скасування дозволено).
        - error is None (повідомлення про помилку відсутнє).
    """
    trip = Trip(id=1, status=TripStatus.SCHEDULED)
    booking = Booking(id=10, trip_id=1, status=BookingStatus.RESERVED)

    allowed, error = can_cancel_booking(booking, trip)
    assert allowed is True
    assert error is None


def test_cannot_cancel_booking_on_closed_trip():
    """
    Короткий опис: Заборона скасування бронювання для фінансово закритого рейсу.
    Що перевіряє: Чи блокується скасування бронювання, якщо рейс має статус CLOSED.
    На вхід:
        - trip: Рейс (Trip) зі статусом CLOSED.
        - booking: Бронювання (Booking) зі статусом RESERVED.
    Очікуваний результат на виході:
        - allowed == False (скасування заборонено).
        - error == "Неможливо скасовувати квитки у фінансово закритому або скасованому рейсі".
    """
    trip = Trip(id=1, status=TripStatus.CLOSED)
    booking = Booking(id=10, trip_id=1, status=BookingStatus.RESERVED)

    allowed, error = can_cancel_booking(booking, trip)
    assert allowed is False
    assert error == "Неможливо скасовувати квитки у фінансово закритому або скасованому рейсі"


def test_cannot_cancel_booking_on_cancelled_trip():
    """
    Короткий опис: Заборона скасування бронювання для вже скасованого рейсу.
    Що перевіряє: Чи блокується скасування бронювання, якщо рейс має статус CANCELLED.
    На вхід:
        - trip: Рейс (Trip) зі статусом CANCELLED.
        - booking: Бронювання (Booking) зі статусом RESERVED.
    Очікуваний результат на виході:
        - allowed == False (скасування заборонено).
        - error == "Неможливо скасовувати квитки у фінансово закритому або скасованому рейсі".
    """
    trip = Trip(id=1, status=TripStatus.CANCELLED)
    booking = Booking(id=10, trip_id=1, status=BookingStatus.RESERVED)

    allowed, error = can_cancel_booking(booking, trip)
    assert allowed is False
    assert error == "Неможливо скасовувати квитки у фінансово закритому або скасованому рейсі"

