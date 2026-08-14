import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.models import User, UserRole, Trip, TripStatus, Booking, BookingType, BookingSource, BookingStatus, PaymentMethod


@pytest.mark.asyncio
async def test_passenger_booking_creation_and_my_bookings(db_session: AsyncSession, sample_trip: Trip):
    passenger = User(
        phone="+380971118899",
        full_name="Booking Pax",
        role=UserRole.PASSENGER,
        telegram_id=88112233,
        is_active=True,
    )
    db_session.add(passenger)
    await db_session.commit()

    sample_trip.status = TripStatus.SCHEDULED
    sample_trip.departure_time = datetime.now(timezone.utc) + timedelta(hours=5)
    await db_session.commit()

    class SessionContext:
        async def __aenter__(self):
            return db_session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("app.api.bookings.async_session_maker", return_value=SessionContext()), \
         patch("app.api.bookings.manager.broadcast", new_callable=AsyncMock):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. POST /api/bookings/ (Create passenger booking)
            resp_create = await client.post(
                "/api/bookings/",
                json={
                    "telegram_id": passenger.telegram_id,
                    "trip_id": sample_trip.id,
                    "requested_seats": 2,
                    "payment_method": "CASH",
                },
            )
            assert resp_create.status_code == 200
            assert "Успішно заброньовано" in resp_create.json()["message"]

            # 2. GET /api/bookings/my/{telegram_id}
            resp_my = await client.get(f"/api/bookings/my/{passenger.telegram_id}")
            assert resp_my.status_code == 200
            bookings_list = resp_my.json()
            assert len(bookings_list) == 2
            booking_id = bookings_list[0]["id"]

            # 3. PATCH /api/bookings/{booking_id}/cancel
            resp_cancel = await client.patch(
                f"/api/bookings/{booking_id}/cancel",
                params={"telegram_id": passenger.telegram_id},
            )
            assert resp_cancel.status_code == 200
            assert "успішно скасовано" in resp_cancel.json()["message"]

            # 4. PATCH /api/bookings/{booking_id}/status (Boarding status update by driver)
            other_booking_id = bookings_list[1]["id"]
            resp_status = await client.patch(
                f"/api/bookings/{other_booking_id}/status",
                json={"status": "BOARDED"},
            )
            assert resp_status.status_code == 200


@pytest.mark.asyncio
async def test_driver_quick_sales_flow(db_session: AsyncSession, sample_trip: Trip):
    driver = User(
        phone="+380972223344",
        full_name="Quick Sales Driver",
        role=UserRole.DRIVER,
        telegram_id=77665544,
        is_active=True,
    )
    db_session.add(driver)
    await db_session.commit()

    sample_trip.driver_id = driver.id
    sample_trip.status = TripStatus.BOARDING
    sample_trip.seats_limit_snapshot = 2
    sample_trip.standing_limit_snapshot = 5
    await db_session.commit()

    class SessionContext:
        async def __aenter__(self):
            return db_session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("app.api.bookings.async_session_maker", return_value=SessionContext()), \
         patch("app.api.bookings.manager.broadcast", new_callable=AsyncMock):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. POST /api/bookings/seated (Quick sale seated)
            resp_seated = await client.post(
                "/api/bookings/seated",
                json={"telegram_id": driver.telegram_id, "trip_id": sample_trip.id},
            )
            assert resp_seated.status_code == 200

            resp_seated_2 = await client.post(
                "/api/bookings/seated",
                json={"telegram_id": driver.telegram_id, "trip_id": sample_trip.id},
            )
            assert resp_seated_2.status_code == 200

            # 2. POST /api/bookings/standing (Quick sale standing after seated is full)
            resp_standing = await client.post(
                "/api/bookings/standing",
                json={"telegram_id": driver.telegram_id, "trip_id": sample_trip.id},
            )
            assert resp_standing.status_code == 200

            # 3. POST /api/bookings/parcel (Quick sale parcel)
            resp_parcel = await client.post(
                "/api/bookings/parcel",
                json={
                    "telegram_id": driver.telegram_id,
                    "trip_id": sample_trip.id,
                    "description": "Important documents",
                    "price": 120.0,
                },
            )
            assert resp_parcel.status_code == 200
