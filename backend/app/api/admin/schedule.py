from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_admin_access
from app.db.database import get_db
from app.db.models import TripStatus, User
from app.schemas.admin import (
    AdminBookingResponse,
    AdminDashboardResponse,
    AdminOfflineBookingCreate,
    AdminTripCreate,
    AdminTripUpdate,
    AdminTripResponse,
    AdminTripStatusUpdate,
    AdminUserResponse,
)
from app.services import admin_use_cases

router = APIRouter(tags=["Admin Schedule"])


@router.get("/dashboard", response_model=AdminDashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.dashboard(db)


@router.get("/trips", response_model=list[AdminTripResponse])
async def get_trips(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.list_trips(db)


@router.post("/trips", response_model=AdminTripResponse)
async def create_trip(
    payload: AdminTripCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.create_trip(db, payload, current_user)


@router.put("/trips/{trip_id}", response_model=AdminTripResponse)
async def update_trip(
    trip_id: int,
    payload: AdminTripUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.update_trip(
        db=db,
        trip_id=trip_id,
        payload=payload,
        actor=current_user,
    )


@router.patch("/trips/{trip_id}/status", response_model=AdminTripResponse)
async def change_trip_status(
    trip_id: int,
    payload: AdminTripStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.update_trip_status(db, trip_id, payload.status, current_user)


@router.post("/trips/{trip_id}/cancel", response_model=AdminTripResponse)
async def cancel_trip(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.update_trip_status(db, trip_id, TripStatus.CANCELLED, current_user)


@router.get("/bookings", response_model=list[AdminBookingResponse])
async def get_bookings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.list_bookings(db)


@router.post("/bookings/offline", response_model=AdminBookingResponse)
async def create_offline_booking(
    payload: AdminOfflineBookingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.create_offline_booking(
        db=db,
        actor=current_user,
        trip_id=payload.trip_id,
        phone=payload.phone,
        full_name=payload.full_name,
        source=payload.source,
        seats=payload.seats,
    )


@router.patch("/bookings/{booking_id}/cancel", response_model=AdminBookingResponse)
async def cancel_booking(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.cancel_booking(db, booking_id, current_user)


@router.get("/users", response_model=list[AdminUserResponse])
async def get_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.list_staff(db)
