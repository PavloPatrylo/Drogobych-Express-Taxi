import pytest
# pyrefly: ignore [missing-import]
import pytest_asyncio
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserRole, Trip, TripStatus, Booking, BookingType, BookingSource, BookingStatus, PaymentMethod
from app.schemas.admin import (
    AdminManifestBookingCreate,
)
from app.services.admin_use_cases import (
    get_trip_manifest_use_case,
    create_manifest_booking_use_case,
    update_booking_status_use_case,
    create_offline_booking,
)


@pytest.mark.asyncio
async def test_get_trip_manifest_success_and_not_found(db_session: AsyncSession, sample_trip: Trip):
    manifest = await get_trip_manifest_use_case(db_session, sample_trip.id)
    assert manifest.trip.id == sample_trip.id
    assert manifest.seated_count == 0
    assert manifest.seated_limit == sample_trip.seats_limit_snapshot

    with pytest.raises(HTTPException) as exc_info:
        await get_trip_manifest_use_case(db_session, 999999)
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_manifest_booking_and_status_update(
    db_session: AsyncSession, sample_trip: Trip, dispatcher_user: User
):
    manifest_booking_payload = AdminManifestBookingCreate(
        booking_type=BookingType.SEATED,
        source=BookingSource.PHONE,
        payment_method=PaymentMethod.CASH,
        phone="0971234567",
        full_name="John Manifest",
        seats=2,
        comment="Front seats requested",
    )

    booking_resp = await create_manifest_booking_use_case(
        db_session, sample_trip.id, manifest_booking_payload, dispatcher_user
    )

    assert booking_resp.trip_id == sample_trip.id
    assert booking_resp.passenger_phone == "+380971234567"
    assert booking_resp.passengers_count == 2
    assert booking_resp.amount_paid == sample_trip.price_seated * 2

    # Check manifest updated counts
    manifest = await get_trip_manifest_use_case(db_session, sample_trip.id)
    assert manifest.seated_count == 2
    assert manifest.total_revenue == sample_trip.price_seated * 2

    # Update status to BOARDED
    updated_b = await update_booking_status_use_case(
        db_session, booking_resp.id, BookingStatus.BOARDED, dispatcher_user
    )
    assert updated_b.status == BookingStatus.BOARDED


@pytest.mark.asyncio
async def test_create_manifest_booking_errors(
    db_session: AsyncSession, sample_trip: Trip, dispatcher_user: User, passenger_user: User
):
    payload = AdminManifestBookingCreate(
        booking_type=BookingType.SEATED,
        source=BookingSource.PHONE,
        phone="0970001122",
        seats=100,  # Exceeds capacity
    )

    # Exceeds capacity
    with pytest.raises(HTTPException) as exc1:
        await create_manifest_booking_use_case(db_session, sample_trip.id, payload, dispatcher_user)
    assert exc1.value.status_code == status.HTTP_400_BAD_REQUEST

    # Forbidden for passenger
    with pytest.raises(HTTPException) as exc2:
        await create_manifest_booking_use_case(db_session, sample_trip.id, payload, passenger_user)
    assert exc2.value.status_code == status.HTTP_403_FORBIDDEN

    # Finalized trip
    sample_trip.status = TripStatus.CLOSED
    await db_session.commit()
    with pytest.raises(HTTPException) as exc3:
        await create_manifest_booking_use_case(db_session, sample_trip.id, payload, dispatcher_user)
    assert exc3.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_create_offline_booking(
    db_session: AsyncSession, sample_trip: Trip, dispatcher_user: User
):
    resp = await create_offline_booking(
        db_session,
        actor=dispatcher_user,
        trip_id=sample_trip.id,
        phone="0979998877",
        full_name="Offline Guest",
        source=BookingSource.PHONE,
        seats=1,
    )
    assert resp.trip_id == sample_trip.id
    assert resp.passenger_phone == "+380979998877"
    assert resp.passengers_count == 1
