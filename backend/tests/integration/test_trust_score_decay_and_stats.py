"""
Integration tests for user trust score decay, stats refreshing, and cancellation penalty isolation.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import (
    Trip, TripStatus, Booking, BookingType, BookingSource, 
    BookingStatus, PaymentMethod, User, UserRole, UserStats, Vehicle, Location
)
from app.services import admin_use_cases


@pytest.mark.asyncio
async def test_trust_score_decay_on_noshow(db_session: AsyncSession, admin_user: User):
    """
    Перевіряє зниження Trust Score пасажира при повторних неявках (NOSHOW):
    100% -> 75% -> 50% -> 25% -> 0%.
    """
    passenger = User(
        phone="+380977001001",
        full_name="Пасажир-Прогульник",
        role=UserRole.PASSENGER,
        is_active=True,
    )
    driver = User(phone="+380977001002", full_name="Водій Трасту", role=UserRole.DRIVER, is_active=True)
    from_loc = Location(name="Drohobych_Trust")
    to_loc = Location(name="Lviv_Trust")
    vehicle = Vehicle(model="Sprinter Trust", plate_number="BC7001AA", total_seats=18, total_standing=5)

    db_session.add_all([passenger, driver, from_loc, to_loc, vehicle])
    await db_session.commit()

    trip = Trip(
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        departure_time=admin_use_cases._combine_date_time("2026-12-10", "14:00"),
        status=TripStatus.COMPLETED,
        seats_limit_snapshot=18,
        standing_limit_snapshot=5,
        price_seated=150.0,
        price_standing=100.0,
    )
    db_session.add(trip)
    await db_session.commit()

    # Створимо 3 неявки (NOSHOW) для даного пасажира
    for i in range(3):
        b = Booking(
            trip_id=trip.id,
            passenger_id=passenger.id,
            created_by_id=admin_user.id,
            booking_type=BookingType.SEATED,
            source=BookingSource.PHONE,
            status=BookingStatus.NOSHOW,
            payment_method=PaymentMethod.CASH,
            passengers_count=1,
            amount_paid=150.0,
        )
        db_session.add(b)

    await db_session.commit()

    # Оновлюємо статистику користувача
    stats = await admin_use_cases.refresh_user_stats(db_session, passenger.id)
    
    assert stats.total_noshows == 3
    # Формула: 100 - (noshows * 25) => 100 - (3 * 25) = 25
    assert stats.trust_score_cached == 25


@pytest.mark.asyncio
async def test_cancelled_by_admin_does_not_penalize_trust_score(db_session: AsyncSession, admin_user: User):
    """
    Перевіряє, що якщо рейс/квиток скасовано адміном/диспетчером,
    це не штрафує Trust Score (не вважається NOSHOW).
    """
    passenger = User(
        phone="+380977002001",
        full_name="Чесний Пасажир",
        role=UserRole.PASSENGER,
        is_active=True,
    )
    driver = User(phone="+380977002002", full_name="Водій Скасувань", role=UserRole.DRIVER, is_active=True)
    from_loc = Location(name="Drohobych_Cancel")
    to_loc = Location(name="Lviv_Cancel")
    vehicle = Vehicle(model="Sprinter Cancel", plate_number="BC7002AA", total_seats=18, total_standing=5)

    db_session.add_all([passenger, driver, from_loc, to_loc, vehicle])
    await db_session.commit()

    trip = Trip(
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        departure_time=admin_use_cases._combine_date_time("2026-12-11", "15:00"),
        status=TripStatus.CANCELLED,
        seats_limit_snapshot=18,
        standing_limit_snapshot=5,
        price_seated=150.0,
        price_standing=100.0,
    )
    db_session.add(trip)
    await db_session.commit()

    b_cancelled = Booking(
        trip_id=trip.id,
        passenger_id=passenger.id,
        created_by_id=admin_user.id,
        booking_type=BookingType.SEATED,
        source=BookingSource.PHONE,
        status=BookingStatus.CANCELLED,
        payment_method=PaymentMethod.CASH,
        passengers_count=1,
        amount_paid=150.0,
    )
    db_session.add(b_cancelled)
    await db_session.commit()

    stats = await admin_use_cases.refresh_user_stats(db_session, passenger.id)

    assert stats.total_noshows == 0
    # Оскільки неявок (NOSHOW) 0, Trust Score залишається 100
    assert stats.trust_score_cached == 100
