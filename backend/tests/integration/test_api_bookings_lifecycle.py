import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.database import get_db
from app.db.models import User, UserRole, Trip, TripStatus, Booking, BookingType, BookingSource, BookingStatus
from app.services.auth_service import create_access_token


@pytest.mark.asyncio
async def test_quick_sale_cancellation_api(db_session: AsyncSession, sample_trip: Trip):
    driver = User(phone="+380970001199", full_name="Quick Driver", role=UserRole.DRIVER, telegram_id=99001122, is_active=True)
    db_session.add(driver)
    await db_session.commit()

    sample_trip.driver_id = driver.id
    sample_trip.status = TripStatus.BOARDING
    await db_session.commit()

    # Add quick sale standing booking
    booking = Booking(
        trip_id=sample_trip.id,
        passenger_id=None,
        created_by_id=driver.id,
        booking_type=BookingType.STANDING,
        source=BookingSource.DRIVER,
        status=BookingStatus.BOARDED,
        passengers_count=1,
        amount_paid=100.0,
    )
    db_session.add(booking)
    await db_session.commit()

    class SessionContext:
        async def __aenter__(self):
            return db_session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("app.api.bookings.async_session_maker", return_value=SessionContext()):
        with patch("app.api.bookings.manager.broadcast", new_callable=AsyncMock):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                # Cancel quick sale
                resp_del = await client.delete(
                    f"/api/bookings/{booking.id}/quick-sale",
                    params={"telegram_id": driver.telegram_id},
                )
                assert resp_del.status_code == 200

                # 404 for deleted booking
                resp_404 = await client.delete(
                    f"/api/bookings/{booking.id}/quick-sale",
                    params={"telegram_id": driver.telegram_id},
                )
                assert resp_404.status_code == 404
