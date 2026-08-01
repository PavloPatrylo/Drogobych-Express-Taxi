from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_admin_access, check_owner_access
from app.db.database import get_db
from app.db.models import TripStatus, User
from app.schemas.admin import (
    AdminBookingResponse,
    AdminDashboardResponse,
    AdminOfflineBookingCreate,
    AdminTripCreate,
    AdminBatchTripCreate,
    AdminTripUpdate,
    AdminTripResponse,
    AdminTripStatusUpdate,
    AdminTripAssignUpdate,
    TripManifestDetailResponse,
    AdminManifestBookingCreate,
    AdminBookingStatusUpdate,
    AdminCloseTripRequest,
    AdminUserResponse,
    SystemConfigResponse,
    SystemConfigUpdate,
    ScheduleTemplateCreate,
    ScheduleTemplateResponse,
    LocationResponse,
)
from app.services import admin_use_cases

router = APIRouter(tags=["Admin Schedule"])


@router.get("/locations", response_model=list[LocationResponse])
async def list_locations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.list_locations_use_case(db)


@router.get("/dashboard", response_model=AdminDashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.dashboard(db)


@router.get("/system-config", response_model=SystemConfigResponse)
async def get_system_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.get_system_config_use_case(db)


@router.put("/system-config", response_model=SystemConfigResponse)
async def update_system_config(
    payload: SystemConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.update_system_config_use_case(db, payload, current_user)


@router.get("/templates", response_model=list[ScheduleTemplateResponse])
async def list_schedule_templates(
    day_type: str | None = None,
    from_location_id: int | None = None,
    to_location_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.list_schedule_templates_use_case(db, day_type, from_location_id, to_location_id)


@router.post("/templates", response_model=ScheduleTemplateResponse)
async def create_schedule_template(
    payload: ScheduleTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_owner_access),
):
    return await admin_use_cases.create_schedule_template_use_case(db, payload, current_user)


@router.delete("/templates/{template_id}")
async def delete_schedule_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_owner_access),
):
    return await admin_use_cases.delete_schedule_template_use_case(db, template_id, current_user)


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


@router.post("/trips/batch", response_model=list[AdminTripResponse])
async def create_batch_trips(
    payload: AdminBatchTripCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.create_batch_trips(db, payload, current_user)


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
@router.put("/trips/{trip_id}/status", response_model=AdminTripResponse)
async def change_trip_status(
    trip_id: int,
    payload: AdminTripStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.update_trip_status(db, trip_id, payload.status, current_user)


@router.patch("/trips/{trip_id}/assign", response_model=AdminTripResponse)
async def update_trip_assign(
    trip_id: int,
    payload: AdminTripAssignUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.update_trip_assign_use_case(db, trip_id, payload, current_user)


@router.get("/trips/{trip_id}/manifest", response_model=TripManifestDetailResponse)
async def get_trip_manifest(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.get_trip_manifest_use_case(db, trip_id)


@router.post("/trips/{trip_id}/manifest/booking", response_model=AdminBookingResponse)
async def create_manifest_booking(
    trip_id: int,
    payload: AdminManifestBookingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.create_manifest_booking_use_case(db, trip_id, payload, current_user)


@router.patch("/bookings/{booking_id}/status", response_model=AdminBookingResponse)
async def change_booking_status(
    booking_id: int,
    payload: AdminBookingStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.update_booking_status_use_case(db, booking_id, payload.status, current_user)


@router.post("/trips/{trip_id}/cancel", response_model=AdminTripResponse)
async def cancel_trip(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.update_trip_status(db, trip_id, TripStatus.CANCELLED, current_user)


@router.post("/trips/{trip_id}/close", response_model=AdminTripResponse)
async def close_trip(
    trip_id: int,
    payload: AdminCloseTripRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.close_trip(
        db=db,
        trip_id=trip_id,
        actor=current_user,
        submitted_cash=payload.submitted_cash,
        submitted_card=payload.submitted_card,
        submitted_amount=payload.submitted_amount,
        comment=payload.comment,
    )


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
