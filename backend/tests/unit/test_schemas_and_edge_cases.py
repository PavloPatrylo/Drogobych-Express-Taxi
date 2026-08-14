import pytest
from datetime import datetime, timedelta, timezone
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserRole, Location, Vehicle, Trip, TripStatus, Booking, BookingStatus, BookingType, BookingSource, PaymentMethod
from app.schemas.admin import AdminOfflineBookingCreate, AdminTripCreate, AdminTripUpdate
from app.services.admin_use_cases import refresh_user_stats, user_to_admin


def test_admin_offline_booking_phone_validation():
    # Valid phone
    b1 = AdminOfflineBookingCreate(trip_id=1, phone="0971234567")
    assert b1.phone == "+380971234567"

    # Valid phone with 380 prefix
    b2 = AdminOfflineBookingCreate(trip_id=1, phone="380971234567")
    assert b2.phone == "+380971234567"

    # Invalid phone - wrong length
    with pytest.raises(ValidationError) as exc1:
        AdminOfflineBookingCreate(trip_id=1, phone="09712345")
    assert "10" in str(exc1.value)

    # Invalid phone - missing 0 prefix
    with pytest.raises(ValidationError) as exc2:
        AdminOfflineBookingCreate(trip_id=1, phone="1971234567")
    assert "0" in str(exc2.value)


def test_admin_trip_date_validation():
    with pytest.raises(ValidationError):
        AdminTripCreate(
            driver_id=1,
            vehicle_id=1,
            route="drohobych-lviv",
            date="invalid-date",
            departure_time="08:00",
        )

    with pytest.raises(ValidationError):
        AdminTripUpdate(
            driver_id=1,
            vehicle_id=1,
            route="drohobych-lviv",
            date="2026-08-15",
            departure_time="invalid-time",
            price_seated=150.0,
            price_standing=100.0,
        )


@pytest.mark.asyncio
async def test_refresh_user_stats_streak_and_early_cancellations(db_session: AsyncSession, admin_user: User):
    passenger = User(phone="+380975556677", full_name="Streak Pass", role=UserRole.PASSENGER, is_active=True)
    from_loc = Location(name="Drohobych")
    to_loc = Location(name="Lviv")
    vehicle = Vehicle(model="Sprinter", plate_number="BC3333EX", total_seats=18, total_standing=5)

    db_session.add_all([passenger, from_loc, to_loc, vehicle])
    await db_session.commit()

    now = datetime(2026, 8, 15, 12, 0)

    # Create 1 NOSHOW booking
    trip_ns = Trip(
        departure_time=now - timedelta(days=10),
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        vehicle_id=vehicle.id,
        driver_id=admin_user.id,
        status=TripStatus.COMPLETED,
        seats_limit_snapshot=18,
        standing_limit_snapshot=5,
        price_seated=150.0,
        price_standing=100.0,
    )
    db_session.add(trip_ns)
    await db_session.commit()

    b_ns = Booking(
        trip_id=trip_ns.id,
        passenger_id=passenger.id,
        created_by_id=admin_user.id,
        booking_type=BookingType.SEATED,
        source=BookingSource.PHONE,
        status=BookingStatus.NOSHOW,
        payment_method=PaymentMethod.CASH,
        passengers_count=1,
        amount_paid=150.0,
    )
    db_session.add(b_ns)
    await db_session.commit()

    # Create 5 BOARDED bookings to build streak and neutralize NOSHOW
    for i in range(1, 6):
        t = Trip(
            departure_time=now - timedelta(days=9 - i),
            from_location_id=from_loc.id,
            to_location_id=to_loc.id,
            vehicle_id=vehicle.id,
            driver_id=admin_user.id,
            status=TripStatus.COMPLETED,
            seats_limit_snapshot=18,
            standing_limit_snapshot=5,
            price_seated=150.0,
            price_standing=100.0,
        )
        db_session.add(t)
        await db_session.commit()

        b = Booking(
            trip_id=t.id,
            passenger_id=passenger.id,
            created_by_id=admin_user.id,
            booking_type=BookingType.SEATED,
            source=BookingSource.PHONE,
            status=BookingStatus.BOARDED,
            payment_method=PaymentMethod.CASH,
            passengers_count=1,
            amount_paid=150.0,
        )
        db_session.add(b)
        await db_session.commit()

    # Create 1 CANCELLED booking > 2 hours in advance
    t_cancel = Trip(
        departure_time=now + timedelta(days=2),
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        vehicle_id=vehicle.id,
        driver_id=admin_user.id,
        status=TripStatus.SCHEDULED,
        seats_limit_snapshot=18,
        standing_limit_snapshot=5,
        price_seated=150.0,
        price_standing=100.0,
    )
    db_session.add(t_cancel)
    await db_session.commit()

    b_cancel = Booking(
        trip_id=t_cancel.id,
        passenger_id=passenger.id,
        created_by_id=admin_user.id,
        booking_type=BookingType.SEATED,
        source=BookingSource.PHONE,
        status=BookingStatus.CANCELLED,
        payment_method=PaymentMethod.CASH,
        passengers_count=1,
        amount_paid=150.0,
        created_at=now,
    )
    db_session.add(b_cancel)
    await db_session.commit()

    stats = await refresh_user_stats(db_session, passenger.id)
    await db_session.commit()

    assert stats.total_trips == 5
    assert stats.total_noshows == 1
    assert stats.trust_score_cached >= 100

    # User response formatting
    admin_user_resp = user_to_admin(passenger)
    assert admin_user_resp.trust_score >= 100
