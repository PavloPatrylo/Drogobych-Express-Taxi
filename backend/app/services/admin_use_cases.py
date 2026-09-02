from __future__ import annotations

import csv
import io
import re
from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

KYIV_TZ = ZoneInfo("Europe/Kyiv")

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.db.models import (
    Booking,
    BookingSource,
    BookingStatus,
    BookingType,
    AuditLog,
    Location,
    Trip,
    TripStatus,
    User,
    UserRole,
    Vehicle,
    UserStats,
    SystemConfig,
    ScheduleTemplate,
    DayType,
    PaymentMethod,
)
from app.websocket_manager import manager
from app.schemas.admin import (
    AdminAuditLogResponse,
    AdminBookingResponse,
    AdminTripCreate,
    AdminTripUpdate,
    AdminTripResponse,
    AdminUserResponse,
    AdminVehicleResponse,
    SystemConfigResponse,
    SystemConfigUpdate,
    ScheduleTemplateCreate,
    ScheduleTemplateResponse,
    AdminBatchTripCreate,
    AdminTripAssignUpdate,
    LocationResponse,
    TripManifestDetailResponse,
    AdminManifestBookingCreate,
    AdminBookingStatusUpdate,
    DriverReportItem,
    VehicleReportItem,
)


async def list_locations_use_case(db: AsyncSession) -> list[LocationResponse]:
    drohobych, lviv = await _locations_for_route(db, "drohobych-lviv")
    result = await db.execute(select(Location).order_by(Location.name))
    locs = result.scalars().all()
    valid_locs = [l for l in locs if l.name and len(l.name.strip()) > 1 and not l.name.startswith('?')]
    return [LocationResponse.model_validate(loc) for loc in valid_locs]


async def _get_system_config(db: AsyncSession) -> SystemConfig:
    result = await db.execute(select(SystemConfig).where(SystemConfig.id == 1))
    config = result.scalars().first()
    if not config:
        config = SystemConfig(id=1, price_seated=200.00, price_standing=150.00, price_parcel=100.00)
        db.add(config)
        await db.commit()
        await db.refresh(config)
    return config


async def get_system_config_use_case(db: AsyncSession) -> SystemConfigResponse:
    config = await _get_system_config(db)
    return SystemConfigResponse(
        id=config.id,
        price_seated=_as_float(config.price_seated),
        price_standing=_as_float(config.price_standing),
        price_parcel=_as_float(config.price_parcel),
        updated_at=config.updated_at,
    )


async def update_system_config_use_case(
    db: AsyncSession, payload: SystemConfigUpdate, actor: User
) -> SystemConfigResponse:
    if actor.role not in (UserRole.ADMIN,):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner/Admin permissions required to update prices",
        )
    config = await _get_system_config(db)
    config.price_seated = payload.price_seated
    config.price_standing = payload.price_standing
    config.price_parcel = payload.price_parcel
    config.updated_by_id = actor.id
    await db.commit()
    await db.refresh(config)
    return SystemConfigResponse(
        id=config.id,
        price_seated=_as_float(config.price_seated),
        price_standing=_as_float(config.price_standing),
        price_parcel=_as_float(config.price_parcel),
        updated_at=config.updated_at,
    )


async def list_schedule_templates_use_case(
    db: AsyncSession,
    day_type: str | None = None,
    from_location_id: int | None = None,
    to_location_id: int | None = None,
) -> list[ScheduleTemplateResponse]:
    stmt = select(ScheduleTemplate)
    if day_type:
        stmt = stmt.where(ScheduleTemplate.day_type == DayType(day_type))
    if from_location_id:
        stmt = stmt.where(ScheduleTemplate.from_location_id == from_location_id)
    if to_location_id:
        stmt = stmt.where(ScheduleTemplate.to_location_id == to_location_id)
    stmt = stmt.order_by(ScheduleTemplate.departure_time)
    result = await db.execute(stmt)
    return [ScheduleTemplateResponse.model_validate(t) for t in result.scalars().all()]


async def create_schedule_template_use_case(
    db: AsyncSession, payload: ScheduleTemplateCreate, actor: User
) -> ScheduleTemplateResponse:
    if actor.role not in (UserRole.ADMIN,):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner/Admin permissions required to create templates",
        )

    drohobych, lviv = await _locations_for_route(db, "drohobych-lviv")
    from_loc = await db.get(Location, payload.from_location_id)
    to_loc = await db.get(Location, payload.to_location_id)

    from_id = from_loc.id if from_loc else drohobych.id
    to_id = to_loc.id if to_loc else lviv.id

    if from_id == to_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пункт відправлення та прибуття не можуть бути однаковими",
        )

    dup = await db.execute(
        select(ScheduleTemplate).where(
            ScheduleTemplate.day_type == payload.day_type,
            ScheduleTemplate.from_location_id == from_id,
            ScheduleTemplate.to_location_id == to_id,
            ScheduleTemplate.departure_time == payload.departure_time,
        )
    )
    if dup.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Шаблон на цей час та напрямок вже існує",
        )

    template = ScheduleTemplate(
        day_type=payload.day_type,
        from_location_id=from_id,
        to_location_id=to_id,
        departure_time=payload.departure_time,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return ScheduleTemplateResponse.model_validate(template)


async def delete_schedule_template_use_case(db: AsyncSession, template_id: int, actor: User):
    if actor.role not in (UserRole.ADMIN,):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner/Admin permissions required to delete templates",
        )
    template = await db.get(ScheduleTemplate, template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    await db.delete(template)
    await db.commit()
    return {"message": "Template deleted"}


async def create_trip(db: AsyncSession, payload: AdminTripCreate, actor: User | None = None) -> AdminTripResponse:
    if actor and actor.role not in (UserRole.ADMIN, UserRole.DISPATCHER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dispatcher/Admin permissions required",
        )

    vehicle = await db.get(Vehicle, payload.vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    driver = await db.get(User, payload.driver_id)
    if not driver or driver.role != UserRole.DRIVER:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")

    departure = _combine_date_time(payload.date, payload.departure_time)
    arrival = _combine_date_time(payload.date, payload.arrival_time)
    
    now_kyiv = datetime.now(KYIV_TZ)
    if departure and departure < now_kyiv:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неможливо створити рейс на дату та час, які вже минули.",
        )

    from_location, to_location = await _locations_for_route(db, payload.route)

    conflict = await db.execute(
        select(Trip).where(
            Trip.departure_time == departure,
            Trip.status != TripStatus.CANCELLED,
            (Trip.driver_id == driver.id) | (Trip.vehicle_id == vehicle.id),
        )
    )
    if conflict.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Driver or vehicle already assigned for {payload.departure_time}")

    sys_config = await _get_system_config(db)
    price_seated = payload.price_seated if payload.price_seated is not None else sys_config.price_seated
    price_standing = payload.price_standing if payload.price_standing is not None else sys_config.price_standing
    price_parcel = payload.price_parcel if payload.price_parcel is not None else sys_config.price_parcel

    trip = Trip(
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        from_location_id=from_location.id,
        to_location_id=to_location.id,
        departure_time=departure,
        arrival_time=arrival,
        status=TripStatus.SCHEDULED,
        seats_limit_snapshot=vehicle.total_seats,
        standing_limit_snapshot=vehicle.total_standing,
        price_seated=price_seated,
        price_standing=price_standing,
        price_parcel=price_parcel,
    )
    db.add(trip)
    await db.flush()
    record_audit_log(
        db,
        actor,
        "TRIP_CREATED",
        entity_type="trip",
        entity_id=trip.id,
        trip_id=trip.id,
        message=f"Created trip {payload.route} {payload.date} {payload.departure_time}",
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Driver or vehicle already assigned",
        )
    await db.refresh(trip, attribute_names=["from_location", "to_location", "closed_by", "driver", "vehicle"])
    return trip_to_admin(trip)


async def create_batch_trips(db: AsyncSession, payload: AdminBatchTripCreate, actor: User) -> list[AdminTripResponse]:
    created_trips = []
    skipped_count = 0
    for item in payload.trips:
        trip_create = AdminTripCreate(
            driver_id=item.driver_id,
            vehicle_id=item.vehicle_id,
            route=item.route,
            date=item.date,
            departure_time=item.departure_time,
            arrival_time=item.arrival_time,
        )
        try:
            res = await create_trip(db, trip_create, actor)
            created_trips.append(res)
        except HTTPException as exc:
            if exc.status_code == status.HTTP_409_CONFLICT:
                skipped_count += 1
                continue
            raise exc

    if not created_trips and skipped_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Усі вибрані рейси на цю дату вже створені у системі!",
        )

    return created_trips

ROUTE_LOCATIONS = {
    "drohobych-lviv": ("Drohobych", "Lviv"),
    "lviv-drohobych": ("Lviv", "Drohobych"),
}

ROUTE_ALIASES = {
    ("дрогобич", "львів"): "drohobych-lviv",
    ("drohobych", "lviv"): "drohobych-lviv",
    ("львів", "дрогобич"): "lviv-drohobych",
    ("lviv", "drohobych"): "lviv-drohobych",
}

ACTIVE_BOOKING_STATUSES = (BookingStatus.RESERVED, BookingStatus.PAID, BookingStatus.BOARDED)


def _as_float(value) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value or 0)


def _to_kyiv(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=KYIV_TZ)
    else:
        dt = dt.astimezone(KYIV_TZ)
    return dt


def _time_string(value: datetime | None) -> str | None:
    if not value:
        return None
    return _to_kyiv(value).strftime("%H:%M")


def _date_string(value: datetime) -> str:
    return _to_kyiv(value).date().isoformat()


def _combine_date_time(date_value: str, time_value: str | None) -> datetime | None:
    if not time_value:
        return None
    try:
        parsed_date = datetime.strptime(date_value, "%Y-%m-%d").date()
        parsed_time = time.fromisoformat(time_value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date or time") from exc
    return datetime.combine(parsed_date, parsed_time, tzinfo=KYIV_TZ)


def _role_value(role: UserRole) -> str:
    return role.value if hasattr(role, "value") else str(role)


def route_slug(from_name: str, to_name: str) -> str:
    return ROUTE_ALIASES.get((from_name.lower(), to_name.lower()), f"{from_name}-{to_name}".lower())


async def _get_or_create_location(db: AsyncSession, name: str) -> Location:
    result = await db.execute(select(Location).where(func.lower(Location.name) == name.lower()))
    location = result.scalars().first()
    if location:
        return location
    location = Location(name=name)
    db.add(location)
    await db.flush()
    return location


async def _locations_for_route(db: AsyncSession, route: str) -> tuple[Location, Location]:
    if route not in ROUTE_LOCATIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown route")
    from_name, to_name = ROUTE_LOCATIONS[route]
    return await _get_or_create_location(db, from_name), await _get_or_create_location(db, to_name)


def vehicle_to_admin(vehicle: Vehicle) -> AdminVehicleResponse:
    return AdminVehicleResponse(
        id=vehicle.id,
        plate=vehicle.plate_number,
        plate_number=vehicle.plate_number,
        model=vehicle.model,
        total_seats=vehicle.total_seats,
        total_standing=vehicle.total_standing,
        is_active=vehicle.is_active,
    )


def user_to_admin(user: User) -> AdminUserResponse:
    stats = user.__dict__.get("stats")
    total_trips = stats.total_trips if stats else 0
    total_noshows = stats.total_noshows if stats else 0
    trust_score = stats.trust_score_cached if stats else 100
    registration_source = "Telegram-бот" if user.telegram_id else "Телефонний дзвінок"

    last_trip_str = None
    if stats and stats.last_trip_date:
        last_trip_str = _date_string(stats.last_trip_date)

    return AdminUserResponse(
        id=user.id,
        name=user.full_name,
        full_name=user.full_name,
        phone=user.phone,
        telegram_id=user.telegram_id,
        role=user.role,
        is_active=user.is_active,
        is_driver=user.role == UserRole.DRIVER,
        total_trips=total_trips,
        total_noshows=total_noshows,
        trust_score=trust_score,
        registration_source=registration_source,
        last_trip_date=last_trip_str,
    )


def trip_to_admin(trip: Trip) -> AdminTripResponse:
    bookings_loaded = 'bookings' in trip.__dict__
    valid_bookings = []
    if bookings_loaded:
        for b in trip.bookings:
            b_status = b.status.name if hasattr(b.status, 'name') else str(b.status)
            if b_status not in ('CANCELLED', 'NOSHOW'):
                valid_bookings.append(b)

    booked_seats = sum(b.passengers_count for b in valid_bookings if b.booking_type == BookingType.SEATED)
    booked_standing = sum(b.passengers_count for b in valid_bookings if b.booking_type == BookingType.STANDING)
    parcels_count = sum(b.passengers_count for b in valid_bookings if b.booking_type == BookingType.PARCEL)
    total_revenue = sum(_as_float(b.amount_paid) for b in valid_bookings)

    return AdminTripResponse(
        id=trip.id,
        driver_id=trip.driver_id,
        vehicle_id=trip.vehicle_id,
        from_location_id=trip.from_location_id,
        to_location_id=trip.to_location_id,
        route=route_slug(trip.from_location.name, trip.to_location.name),
        date=_date_string(trip.departure_time),
        departure_time=_time_string(trip.departure_time) or "",
        arrival_time=_time_string(trip.arrival_time),
        status=trip.status,
        seats_limit_snapshot=trip.seats_limit_snapshot,
        standing_limit_snapshot=trip.standing_limit_snapshot,
        price_seated=_as_float(trip.price_seated),
        price_standing=_as_float(trip.price_standing),
        price_parcel=_as_float(trip.price_parcel) if trip.price_parcel is not None else None,
        submitted_amount=_as_float(trip.submitted_amount) if trip.submitted_amount is not None else None,
        submitted_cash=_as_float(trip.submitted_cash) if trip.submitted_cash is not None else None,
        submitted_card=_as_float(trip.submitted_card) if trip.submitted_card is not None else None,
        closed_by_id=trip.closed_by_id,
        closed_by=trip.closed_by.full_name if trip.closed_by else None,
        close_comment=trip.close_comment,
        driver_name=trip.driver.full_name if trip.driver else None,
        driver_phone=trip.driver.phone if trip.driver else None,
        vehicle_plate=trip.vehicle.plate_number if trip.vehicle else None,
        vehicle_model=trip.vehicle.model if trip.vehicle else None,
        booked_seats=booked_seats,
        booked_standing=booked_standing,
        parcels_count=parcels_count,
        total_revenue=total_revenue,
    )


def booking_to_admin(booking: Booking, passenger: User | None = None) -> AdminBookingResponse:
    pm = getattr(booking, "payment_method", PaymentMethod.CASH) or PaymentMethod.CASH
    return AdminBookingResponse(
        id=booking.id,
        trip_id=booking.trip_id,
        passenger_id=booking.passenger_id,
        created_by_id=booking.created_by_id,
        booking_type=booking.booking_type,
        source=booking.source,
        status=booking.status,
        payment_method=pm,
        passengers_count=booking.passengers_count,
        amount_paid=_as_float(booking.amount_paid),
        comment=booking.comment,
        created_at=booking.created_at,
        passenger_name=passenger.full_name if passenger else None,
        passenger_phone=passenger.phone if passenger else None,
    )


def audit_log_to_admin(log: AuditLog) -> AdminAuditLogResponse:
    trip_label = "—"
    if log.trip and log.trip.from_location and log.trip.to_location:
        trip_label = (
            f"{_time_string(log.trip.departure_time)} "
            f"{log.trip.from_location.name} -> {log.trip.to_location.name}"
        )

    return AdminAuditLogResponse(
        id=log.id,
        created_at=log.created_at,
        time=log.created_at.strftime("%d.%m.%Y %H:%M") if log.created_at else "",
        action=log.action,
        entity_type=log.entity_type,
        entity_id=log.entity_id,
        trip_id=log.trip_id,
        passenger_id=log.passenger_id,
        trip=trip_label,
        passenger=log.passenger.full_name if log.passenger else "—",
        source=log.source,
        by=log.actor.full_name if log.actor else "System",
        message=log.message,
    )


def record_audit_log(
    db: AsyncSession,
    actor: User | None,
    action: str,
    *,
    entity_type: str | None = None,
    entity_id: int | None = None,
    trip_id: int | None = None,
    passenger_id: int | None = None,
    source: str = "WEB",
    message: str | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor.id if actor else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            trip_id=trip_id,
            passenger_id=passenger_id,
            source=source,
            message=message,
        )
    )


async def list_audit_logs(
    db: AsyncSession,
    limit: int = 100,
    trip_id: int | None = None,
    passenger_id: int | None = None,
) -> list[AdminAuditLogResponse]:
    stmt = (
        select(AuditLog)
        .options(
            selectinload(AuditLog.actor),
            selectinload(AuditLog.passenger),
            selectinload(AuditLog.trip).selectinload(Trip.from_location),
            selectinload(AuditLog.trip).selectinload(Trip.to_location),
        )
        .order_by(AuditLog.created_at.desc())
        .limit(min(max(limit, 1), 500))
    )
    if trip_id is not None:
        stmt = stmt.where(AuditLog.trip_id == trip_id)
    if passenger_id is not None:
        stmt = stmt.where(AuditLog.passenger_id == passenger_id)

    result = await db.execute(stmt)
    return [audit_log_to_admin(log) for log in result.scalars().all()]


async def list_vehicles(db: AsyncSession) -> list[AdminVehicleResponse]:
    result = await db.execute(select(Vehicle).order_by(Vehicle.plate_number))
    return [vehicle_to_admin(vehicle) for vehicle in result.scalars().all()]


async def list_staff(db: AsyncSession) -> list[AdminUserResponse]:
    result = await db.execute(
        select(User)
        .where(User.role.in_([UserRole.DRIVER, UserRole.DISPATCHER, UserRole.ADMIN]))
        .options(selectinload(User.stats))
        .order_by(User.role, User.full_name)
    )
    return [user_to_admin(user) for user in result.scalars().all()]


async def list_passengers(db: AsyncSession) -> list[AdminUserResponse]:
    result = await db.execute(
        select(User)
        .where(User.role == UserRole.PASSENGER)
        .options(selectinload(User.stats))
        .order_by(User.full_name)
    )
    users = result.scalars().all()
    
    for user in users:
        await refresh_user_stats(db, user.id)
        
    await db.commit()

    # Reload users to get updated stats
    result = await db.execute(
        select(User)
        .where(User.role == UserRole.PASSENGER)
        .options(selectinload(User.stats))
        .order_by(User.full_name)
    )
    users = result.scalars().all()
    return [user_to_admin(user) for user in users]


async def list_trips(db: AsyncSession) -> list[AdminTripResponse]:
    result = await db.execute(
        select(Trip)
        .options(
            selectinload(Trip.from_location),
            selectinload(Trip.to_location),
            selectinload(Trip.closed_by),
            selectinload(Trip.driver),
            selectinload(Trip.vehicle),
            selectinload(Trip.bookings),
        )
        .order_by(Trip.departure_time.desc())
    )
    return [trip_to_admin(trip) for trip in result.scalars().all()]


async def list_bookings(db: AsyncSession) -> list[AdminBookingResponse]:
    passenger_alias = aliased(User)
    result = await db.execute(
        select(Booking, passenger_alias)
        .outerjoin(passenger_alias, Booking.passenger_id == passenger_alias.id)
        .order_by(Booking.created_at.desc())
    )
    return [booking_to_admin(booking, passenger) for booking, passenger in result.all()]


async def create_trip(db: AsyncSession, payload: AdminTripCreate, actor: User | None = None) -> AdminTripResponse:
    if actor and actor.role not in (UserRole.ADMIN, UserRole.DISPATCHER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dispatcher/Admin permissions required",
        )

    vehicle = await db.get(Vehicle, payload.vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    driver = await db.get(User, payload.driver_id)
    if not driver or driver.role != UserRole.DRIVER:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")

    departure = _combine_date_time(payload.date, payload.departure_time)
    arrival = _combine_date_time(payload.date, payload.arrival_time)

    now_kyiv = datetime.now(KYIV_TZ)
    if departure and departure < now_kyiv:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неможливо створити рейс на дату та час, які вже минули.",
        )

    from_location, to_location = await _locations_for_route(db, payload.route)

    conflict = await db.execute(
        select(Trip).where(
            Trip.departure_time == departure,
            Trip.status != TripStatus.CANCELLED,
            (Trip.driver_id == driver.id) | (Trip.vehicle_id == vehicle.id),
        )
    )
    if conflict.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Driver or vehicle already assigned")

    cfg = await _get_system_config(db)
    final_price_seated = payload.price_seated if payload.price_seated is not None else _as_float(cfg.price_seated)
    final_price_standing = payload.price_standing if payload.price_standing is not None else _as_float(cfg.price_standing)
    final_price_parcel = payload.price_parcel if payload.price_parcel is not None else _as_float(cfg.price_parcel)

    trip = Trip(
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        from_location_id=from_location.id,
        to_location_id=to_location.id,
        departure_time=departure,
        arrival_time=arrival,
        status=TripStatus.SCHEDULED,
        seats_limit_snapshot=vehicle.total_seats,
        standing_limit_snapshot=vehicle.total_standing,
        price_seated=final_price_seated,
        price_standing=final_price_standing,
        price_parcel=final_price_parcel,
    )
    db.add(trip)
    await db.flush()
    record_audit_log(
        db,
        actor,
        "TRIP_CREATED",
        entity_type="trip",
        entity_id=trip.id,
        trip_id=trip.id,
        message=f"Created trip {payload.route} {payload.date} {payload.departure_time}",
    )
    try:
        await db.commit()
        await manager.broadcast("TRIP_MUTATED", {"trip_id": trip.id})
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Driver or vehicle already assigned",
        )
    await db.refresh(trip, attribute_names=["from_location", "to_location", "closed_by"])
    return trip_to_admin(trip)


async def update_trip(
    db: AsyncSession,
    trip_id: int,
    payload: AdminTripUpdate,
    actor: User | None = None,
) -> AdminTripResponse:
    if actor and actor.role not in (UserRole.ADMIN, UserRole.DISPATCHER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dispatcher/Admin permissions required",
        )

    # 1. Lock the trip row to prevent race conditions
    result = await db.execute(
        select(Trip)
        .where(Trip.id == trip_id)
        .options(selectinload(Trip.from_location), selectinload(Trip.to_location), selectinload(Trip.closed_by))
        .with_for_update()
    )
    trip = result.scalars().first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    # Only SCHEDULED or BOARDING trips can be edited
    if trip.status not in (TripStatus.SCHEDULED, TripStatus.BOARDING):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only SCHEDULED or BOARDING trips can be edited",
        )

    vehicle = await db.get(Vehicle, payload.vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    driver = await db.get(User, payload.driver_id)
    if not driver or driver.role != UserRole.DRIVER:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")

    departure = _combine_date_time(payload.date, payload.departure_time)
    arrival = _combine_date_time(payload.date, payload.arrival_time)

    now_kyiv = datetime.now(KYIV_TZ)
    if departure and departure < now_kyiv:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неможливо перенести рейс на дату та час, які вже минули.",
        )

    from_location, to_location = await _locations_for_route(db, payload.route)

    # Check conflict, excluding the current trip
    conflict = await db.execute(
        select(Trip).where(
            Trip.id != trip.id,
            Trip.departure_time == departure,
            Trip.status != TripStatus.CANCELLED,
            (Trip.driver_id == driver.id) | (Trip.vehicle_id == vehicle.id),
        )
    )
    if conflict.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Driver or vehicle already assigned")

    # If vehicle changed, update snapshot limits with overbooking validation
    if trip.vehicle_id != vehicle.id:
        seated_res = await db.execute(
            select(func.sum(Booking.passengers_count)).where(
                Booking.trip_id == trip.id,
                Booking.booking_type == BookingType.SEATED,
                Booking.status.in_(ACTIVE_BOOKING_STATUSES),
            )
        )
        booked_seated = seated_res.scalar() or 0
        if vehicle.total_seats < booked_seated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Неможливо замінити авто на {vehicle.plate_number} ({vehicle.total_seats} місць): на рейс вже заброньовано {booked_seated} сидячих місць!",
            )

        standing_res = await db.execute(
            select(func.sum(Booking.passengers_count)).where(
                Booking.trip_id == trip.id,
                Booking.booking_type == BookingType.STANDING,
                Booking.status.in_(ACTIVE_BOOKING_STATUSES),
            )
        )
        booked_standing = standing_res.scalar() or 0
        if vehicle.total_standing < booked_standing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Неможливо замінити авто на {vehicle.plate_number} ({vehicle.total_standing} стоячих): на рейс вже заброньовано {booked_standing} стоячих місць!",
            )

        trip.seats_limit_snapshot = vehicle.total_seats
        trip.standing_limit_snapshot = vehicle.total_standing

    # Prevent changing trip prices if there are active bookings
    cfg = await _get_system_config(db)
    cur_price_seated = _as_float(trip.price_seated)
    cur_price_standing = _as_float(trip.price_standing)
    cur_price_parcel = _as_float(trip.price_parcel) if trip.price_parcel is not None else _as_float(cfg.price_parcel)

    new_price_seated = float(payload.price_seated)
    new_price_standing = float(payload.price_standing)
    new_price_parcel = float(payload.price_parcel) if payload.price_parcel is not None else cur_price_parcel

    if (new_price_seated != cur_price_seated or 
        new_price_standing != cur_price_standing or 
        new_price_parcel != cur_price_parcel):
        booked_res = await db.execute(
            select(func.count(Booking.id)).where(
                Booking.trip_id == trip.id,
                Booking.status.in_(ACTIVE_BOOKING_STATUSES),
            )
        )
        if (booked_res.scalar() or 0) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неможливо змінити ціну рейсу, на який вже є заброньовані місця. Якщо ціна вказана помилково, скасуйте рейс та створіть новий.",
            )

    trip.driver_id = driver.id
    trip.vehicle_id = vehicle.id
    trip.from_location_id = from_location.id
    trip.to_location_id = to_location.id
    trip.departure_time = departure
    trip.arrival_time = arrival
    trip.price_seated = payload.price_seated
    trip.price_standing = payload.price_standing
    if payload.price_parcel is not None:
        trip.price_parcel = payload.price_parcel

    record_audit_log(
        db,
        actor,
        "TRIP_UPDATED",
        entity_type="trip",
        entity_id=trip.id,
        trip_id=trip.id,
        message=f"Updated trip {payload.route} {payload.date} {payload.departure_time}",
    )
    try:
        await db.commit()
        await manager.broadcast("TRIP_MUTATED", {"trip_id": trip.id})
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Driver or vehicle already assigned",
        )
    await db.refresh(trip, attribute_names=["from_location", "to_location", "closed_by"])
    return trip_to_admin(trip)


async def update_trip_status(
    db: AsyncSession,
    trip_id: int,
    new_status: TripStatus,
    actor: User | None = None,
) -> AdminTripResponse:
    if actor and actor.role not in (UserRole.ADMIN, UserRole.DISPATCHER, UserRole.DRIVER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Driver, Dispatcher or Admin permissions required",
        )

    if new_status == TripStatus.CLOSED and actor and actor.role == UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Лише Диспетчер або Адмін може закрити рейс",
        )

    # SELECT ... FOR UPDATE (locks row to prevent race conditions)
    result = await db.execute(
        select(Trip)
        .where(Trip.id == trip_id)
        .options(
            selectinload(Trip.from_location),
            selectinload(Trip.to_location),
            selectinload(Trip.closed_by),
            selectinload(Trip.driver),
            selectinload(Trip.vehicle),
            selectinload(Trip.bookings),
        )
        .with_for_update()
    )
    trip = result.scalars().first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    previous_status = trip.status

    if previous_status in (TripStatus.COMPLETED, TripStatus.CLOSED):
        if new_status != TripStatus.CLOSED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Зміна статусу заблокована: якщо рейс вже завершено водієм або закрито, його стан не можна змінювати.",
            )

    if new_status == TripStatus.CLOSED and previous_status != TripStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Закрити рейс (фінансове закриття) можна лише після його завершення (стан 'Завершено')",
        )

    if new_status == TripStatus.CANCELLED:
        if trip.status in (TripStatus.CLOSED, TripStatus.CANCELLED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trip already finalized or cancelled",
            )
        trip.status = TripStatus.CANCELLED
        bookings_res = await db.execute(
            select(Booking).where(
                Booking.trip_id == trip.id,
                Booking.status.in_([BookingStatus.RESERVED, BookingStatus.PAID, BookingStatus.BOARDED]),
            )
        )
        active_bookings = bookings_res.scalars().all()
        for booking in active_bookings:
            booking.status = BookingStatus.CANCELLED

        passenger_ids = [b.passenger_id for b in active_bookings if b.passenger_id]
        if passenger_ids:
            passengers_res = await db.execute(
                select(User.telegram_id).where(
                    User.id.in_(passenger_ids),
                    User.telegram_id.isnot(None),
                )
            )
            telegram_ids = [t_id for (t_id,) in passengers_res.all() if t_id]

            if telegram_ids:
                route_title = (
                    f"{trip.from_location.name} -> {trip.to_location.name}"
                    if (trip.from_location and trip.to_location)
                    else trip.route
                )
                date_str = _date_string(trip.departure_time)
                time_str = _time_string(trip.departure_time)

                cancel_msg = (
                    f"⚠️ **РЕЙС СКАСОВАНО**\n\n"
                    f"Шановний пасажире, на жаль, рейс **{route_title}** "
                    f"на **{date_str} о {time_str}** скасовано диспетчером.\n\n"
                    f"Для уточнення деталей чи перебронювання квитків зв'яжіться з диспетчером."
                )

                try:
                    from app.api.admin.broadcast import run_telegram_broadcast
                    import asyncio
                    asyncio.create_task(run_telegram_broadcast(telegram_ids, cancel_msg))
                except Exception as e:
                    print(f"Failed to queue telegram cancel notifications: {e}")
    else:
        if trip.status == TripStatus.CLOSED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change status of a closed trip",
            )
        trip.status = new_status
        if new_status == TripStatus.COMPLETED:
            bookings = await db.execute(
                select(Booking).where(
                    Booking.trip_id == trip.id,
                    Booking.status.in_([BookingStatus.RESERVED, BookingStatus.PAID]),
                )
            )
            for booking in bookings.scalars().all():
                booking.status = BookingStatus.NOSHOW

    record_audit_log(
        db,
        actor,
        "TRIP_STATUS_UPDATED",
        entity_type="trip",
        entity_id=trip.id,
        trip_id=trip.id,
        message=f"Changed status from {previous_status.value} to {new_status.value}",
    )
    await db.commit()
    await manager.broadcast("TRIP_MUTATED", {"trip_id": trip.id})
    await db.refresh(trip, attribute_names=["from_location", "to_location", "closed_by", "driver", "vehicle"])
    return trip_to_admin(trip)


async def update_trip_assign_use_case(
    db: AsyncSession,
    trip_id: int,
    payload: AdminTripAssignUpdate,
    actor: User | None = None,
) -> AdminTripResponse:
    if actor and actor.role not in (UserRole.ADMIN, UserRole.DISPATCHER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dispatcher/Admin permissions required",
        )

    result = await db.execute(
        select(Trip)

        .where(Trip.id == trip_id)
        .options(
            selectinload(Trip.from_location),
            selectinload(Trip.to_location),
            selectinload(Trip.closed_by),
            selectinload(Trip.driver),
            selectinload(Trip.vehicle),
        )
        .with_for_update()
    )
    trip = result.scalars().first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    new_driver_id = payload.driver_id if payload.driver_id is not None else trip.driver_id
    new_vehicle_id = payload.vehicle_id if payload.vehicle_id is not None else trip.vehicle_id

    driver = await db.get(User, new_driver_id)
    if not driver or driver.role != UserRole.DRIVER:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")

    vehicle = await db.get(Vehicle, new_vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    conflict = await db.execute(
        select(Trip).where(
            Trip.id != trip.id,
            Trip.departure_time == trip.departure_time,
            Trip.status != TripStatus.CANCELLED,
            (Trip.driver_id == driver.id) | (Trip.vehicle_id == vehicle.id),
        )
    )
    if conflict.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Driver or vehicle already assigned to another trip at this time",
        )

    if trip.vehicle_id != vehicle.id:
        seated_res = await db.execute(
            select(func.sum(Booking.passengers_count)).where(
                Booking.trip_id == trip.id,
                Booking.booking_type == BookingType.SEATED,
                Booking.status.in_(ACTIVE_BOOKING_STATUSES),
            )
        )
        booked_seated = seated_res.scalar() or 0
        if vehicle.total_seats < booked_seated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Неможливо замінити авто на {vehicle.plate_number} ({vehicle.total_seats} місць): на рейс вже заброньовано {booked_seated} сидячих місць!",
            )

        standing_res = await db.execute(
            select(func.sum(Booking.passengers_count)).where(
                Booking.trip_id == trip.id,
                Booking.booking_type == BookingType.STANDING,
                Booking.status.in_(ACTIVE_BOOKING_STATUSES),
            )
        )
        booked_standing = standing_res.scalar() or 0
        if vehicle.total_standing < booked_standing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Неможливо замінити авто на {vehicle.plate_number} ({vehicle.total_standing} стоячих): на рейс вже заброньовано {booked_standing} стоячих місць!",
            )

        trip.seats_limit_snapshot = vehicle.total_seats
        trip.standing_limit_snapshot = vehicle.total_standing

    trip.driver_id = driver.id
    trip.vehicle_id = vehicle.id

    record_audit_log(
        db,
        actor,
        "TRIP_ASSIGNMENT_UPDATED",
        entity_type="trip",
        entity_id=trip.id,
        trip_id=trip.id,
        message=f"Updated assignment for trip #{trip.id}: Driver={driver.full_name}, Vehicle={vehicle.plate_number}",
    )
    await db.commit()
    await manager.broadcast("TRIP_MUTATED", {"trip_id": trip.id})
    await db.refresh(trip, attribute_names=["from_location", "to_location", "closed_by", "driver", "vehicle"])
    return trip_to_admin(trip)


async def close_trip(
    db: AsyncSession,
    trip_id: int,
    actor: User,
    submitted_cash: float | None = 0.0,
    submitted_card: float | None = 0.0,
    submitted_amount: float | None = None,
    comment: str | None = None,
) -> AdminTripResponse:
    if actor.role not in (UserRole.ADMIN, UserRole.DISPATCHER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dispatcher/Admin permissions required",
        )

    # SELECT ... FOR UPDATE (locks row to prevent race conditions)
    result = await db.execute(
        select(Trip)
        .where(Trip.id == trip_id)
        .options(
            selectinload(Trip.from_location),
            selectinload(Trip.to_location),
            selectinload(Trip.closed_by),
            selectinload(Trip.driver),
            selectinload(Trip.vehicle),
        )
        .with_for_update()
    )
    trip = result.scalars().first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    if trip.status not in (TripStatus.COMPLETED, TripStatus.CLOSED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Закрити рейс (фінансове закриття) можна лише після його завершення (стан 'Завершено')",
        )

    cash_val = float(submitted_cash or 0.0)
    card_val = float(submitted_card or 0.0)
    total_val = submitted_amount if submitted_amount is not None else (cash_val + card_val)

    trip.status = TripStatus.CLOSED
    trip.closed_by_id = actor.id
    trip.submitted_cash = cash_val
    trip.submitted_card = card_val
    trip.submitted_amount = total_val
    trip.close_comment = comment

    record_audit_log(
        db,
        actor,
        "TRIP_FINANCIALLY_CLOSED",
        entity_type="trip",
        entity_id=trip.id,
        trip_id=trip.id,
        message=f"Financial closure for trip #{trip.id}: Cash={cash_val}₴, Card={card_val}₴, Total={total_val}₴. Note: {comment or '—'}",
    )

    await db.commit()
    await manager.broadcast("TRIP_MUTATED", {"trip_id": trip.id})
    await db.refresh(trip, attribute_names=["from_location", "to_location", "closed_by", "driver", "vehicle"])
    return trip_to_admin(trip)


async def create_offline_booking(
    db: AsyncSession,
    actor: User,
    trip_id: int,
    phone: str,
    full_name: str | None,
    source: BookingSource,
    seats: int,
    payment_method: PaymentMethod = PaymentMethod.CASH,
) -> AdminBookingResponse:
    if actor.role not in (UserRole.ADMIN, UserRole.DISPATCHER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dispatcher/Admin permissions required",
        )

    # SELECT ... FOR UPDATE (locks row to prevent race conditions)
    result = await db.execute(
        select(Trip).where(Trip.id == trip_id).with_for_update()
    )
    trip = result.scalars().first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    # Check trip status: booking only allowed on SCHEDULED or BOARDING trips
    if trip.status not in (TripStatus.SCHEDULED, TripStatus.BOARDING):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking is only allowed on SCHEDULED or BOARDING trips",
        )

    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("380") and len(digits) == 12:
        digits = digits[2:]
    if len(digits) != 10 or not digits.startswith("0"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Номер телефону повинен містити рівно 10 цифр і починатися з 0 (наприклад: 0971234567)",
        )
    formatted_phone = f"+38{digits}"
    raw_phone = digits

    passenger_result = await db.execute(
        select(User).where((User.phone == formatted_phone) | (User.phone == raw_phone))
    )
    passenger = passenger_result.scalars().first()
    if not passenger:
        passenger = User(phone=formatted_phone, full_name=full_name or formatted_phone, role=UserRole.PASSENGER, is_active=True)
        db.add(passenger)
        await db.flush()
    if not passenger.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passenger is blocked")

    booked_result = await db.execute(
        select(func.sum(Booking.passengers_count)).where(
            Booking.trip_id == trip.id,
            Booking.booking_type == BookingType.SEATED,
            Booking.status.in_(ACTIVE_BOOKING_STATUSES),
        )
    )
    booked_seats = booked_result.scalar() or 0
    if trip.seats_limit_snapshot - booked_seats < seats:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough seats")

    pm = payment_method or PaymentMethod.CASH
    booking = Booking(
        trip_id=trip.id,
        passenger_id=passenger.id,
        created_by_id=actor.id,
        booking_type=BookingType.SEATED,
        source=source,
        status=BookingStatus.RESERVED,
        payment_method=pm,
        passengers_count=seats,
        amount_paid=_as_float(trip.price_seated) * seats,
    )
    db.add(booking)
    await db.flush()
    record_audit_log(
        db,
        actor,
        "BOOKING_CREATED",
        entity_type="booking",
        entity_id=booking.id,
        trip_id=trip.id,
        passenger_id=passenger.id,
        source=source.value,
        message=f"Offline booking for {seats} seat(s)",
    )
    await db.commit()
    await manager.broadcast("BOOKING_MUTATED", {"trip_id": trip.id})
    await db.refresh(booking)
    return booking_to_admin(booking, passenger)


async def cancel_booking(
    db: AsyncSession,
    booking_id: int,
    actor: User | None = None,
) -> AdminBookingResponse:
    if actor and actor.role not in (UserRole.ADMIN, UserRole.DISPATCHER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dispatcher/Admin permissions required",
        )

    # Lock booking row first
    result = await db.execute(
        select(Booking)
        .where(Booking.id == booking_id)
        .with_for_update()
    )
    booking = result.scalars().first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    trip = await db.get(Trip, booking.trip_id)
    if trip and trip.status in (TripStatus.CLOSED, TripStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неможливо скасовувати квитки у фінансово закритому або скасованому рейсі",
        )

    # Fetch passenger separately to avoid locking on nullable side of outer join
    passenger = None
    if booking.passenger_id:
        passenger = await db.get(User, booking.passenger_id)
    booking.status = BookingStatus.CANCELLED
    record_audit_log(
        db,
        actor,
        "BOOKING_CANCELLED",
        entity_type="booking",
        entity_id=booking.id,
        trip_id=booking.trip_id,
        passenger_id=booking.passenger_id,
        source="WEB",
    )
    await db.commit()
    await manager.broadcast("BOOKING_MUTATED", {"trip_id": booking.trip_id})
    await promote_waitlist_bookings_use_case(db, booking.trip_id)
    await db.refresh(booking)
    return booking_to_admin(booking, passenger)


async def toggle_passenger(
    db: AsyncSession,
    passenger_id: int,
    is_active: bool | None = None,
    actor: User | None = None,
) -> AdminUserResponse:
    if actor and actor.role not in (UserRole.ADMIN, UserRole.DISPATCHER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dispatcher/Admin permissions required",
        )

    result = await db.execute(
        select(User)
        .where(User.id == passenger_id, User.role == UserRole.PASSENGER)
        .options(selectinload(User.stats))
    )
    passenger = result.scalars().first()
    if not passenger:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passenger not found")
    passenger.is_active = (not passenger.is_active) if is_active is None else is_active
    record_audit_log(
        db,
        actor,
        "PASSENGER_UNBLOCKED" if passenger.is_active else "PASSENGER_BLOCKED",
        entity_type="passenger",
        entity_id=passenger.id,
        passenger_id=passenger.id,
        source="WEB",
    )
    await db.commit()
    await db.refresh(passenger)
    return user_to_admin(passenger)


async def trip_finance_stats(db: AsyncSession, trip_id: int) -> dict:
    result = await db.execute(select(Booking).where(Booking.trip_id == trip_id))
    bookings = result.scalars().all()
    billable = [b for b in bookings if b.status not in (BookingStatus.CANCELLED, BookingStatus.NOSHOW)]
    cash_revenue = sum(_as_float(b.amount_paid) for b in billable if getattr(b, "payment_method", PaymentMethod.CASH) == PaymentMethod.CASH or str(getattr(b, "payment_method", "CASH")) == "CASH")
    card_revenue = sum(_as_float(b.amount_paid) for b in billable if getattr(b, "payment_method", PaymentMethod.CASH) == PaymentMethod.CARD or str(getattr(b, "payment_method", "CARD")) == "CARD")
    return {
        "seated": sum(b.passengers_count for b in billable if b.booking_type == BookingType.SEATED),
        "standing": sum(b.passengers_count for b in billable if b.booking_type == BookingType.STANDING),
        "parcels": sum(b.passengers_count for b in billable if b.booking_type == BookingType.PARCEL),
        "cash_revenue": cash_revenue,
        "card_revenue": card_revenue,
        "revenue": cash_revenue + card_revenue,
    }


async def finance_summary(
    db: AsyncSession,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    trips = await list_trips(db)
    bookings = await list_bookings(db)

    if date_from:
        trips = [t for t in trips if t.date >= date_from]
    if date_to:
        trips = [t for t in trips if t.date <= date_to]

    filtered_trip_ids = {t.id for t in trips}
    billable_bookings = [
        b for b in bookings 
        if b.trip_id in filtered_trip_ids and b.status not in (BookingStatus.CANCELLED, BookingStatus.NOSHOW)
    ]

    total_cash_revenue = sum(
        _as_float(b.amount_paid) for b in billable_bookings 
        if getattr(b, "payment_method", PaymentMethod.CASH) == PaymentMethod.CASH or str(getattr(b, "payment_method", "CASH")) == "CASH"
    )
    total_card_revenue = sum(
        _as_float(b.amount_paid) for b in billable_bookings 
        if getattr(b, "payment_method", PaymentMethod.CASH) == PaymentMethod.CARD or str(getattr(b, "payment_method", "CARD")) == "CARD"
    )
    total_revenue = total_cash_revenue + total_card_revenue
    return {
        "total_revenue": total_revenue,
        "total_cash_revenue": total_cash_revenue,
        "total_card_revenue": total_card_revenue,
        "pending_close": [trip for trip in trips if trip.status == TripStatus.COMPLETED],
        "closed_trips": [trip for trip in trips if trip.status == TripStatus.CLOSED],
    }


async def driver_report_use_case(
    db: AsyncSession,
    date_from: str | None = None,
    date_to: str | None = None,
    driver_id: int | None = None,
) -> list[DriverReportItem]:
    drivers_query = select(User).where(User.role == UserRole.DRIVER)
    if driver_id:
        drivers_query = drivers_query.where(User.id == driver_id)
    res_drivers = await db.execute(drivers_query)
    drivers = res_drivers.scalars().all()

    trips_query = (
        select(Trip)
        .options(selectinload(Trip.bookings), selectinload(Trip.driver))
        .where(Trip.status != TripStatus.CANCELLED)
    )
    if driver_id:
        trips_query = trips_query.where(Trip.driver_id == driver_id)

    res_trips = await db.execute(trips_query)
    all_trips = res_trips.scalars().all()

    filtered_trips = []
    for t in all_trips:
        t_date = _date_string(t.departure_time)
        if date_from and t_date < date_from:
            continue
        if date_to and t_date > date_to:
            continue
        filtered_trips.append(t)

    report_items = []
    for d in drivers:
        d_trips = [t for t in filtered_trips if t.driver_id == d.id]
        completed_count = sum(1 for t in d_trips if t.status in (TripStatus.COMPLETED, TripStatus.CLOSED))
        
        cash_rev = 0.0
        card_rev = 0.0
        passengers_cnt = 0

        for t in d_trips:
            for b in t.bookings:
                if b.status not in (BookingStatus.CANCELLED, BookingStatus.NOSHOW):
                    passengers_cnt += b.passengers_count
                    amt = _as_float(b.amount_paid)
                    pm = getattr(b, "payment_method", PaymentMethod.CASH)
                    if pm == PaymentMethod.CARD or str(pm) == "CARD":
                        card_rev += amt
                    else:
                        cash_rev += amt

        tot_rev = cash_rev + card_rev
        trips_cnt = len(d_trips)
        avg_rev = round(tot_rev / trips_cnt, 2) if trips_cnt > 0 else 0.0

        report_items.append(
            DriverReportItem(
                driver_id=d.id,
                driver_name=d.full_name or d.phone or f"Водій #{d.id}",
                driver_phone=d.phone,
                trips_count=trips_cnt,
                completed_trips_count=completed_count,
                total_passengers=passengers_cnt,
                cash_revenue=cash_rev,
                card_revenue=card_rev,
                total_revenue=tot_rev,
                avg_revenue_per_trip=avg_rev,
            )
        )

    return report_items


async def vehicle_report_use_case(
    db: AsyncSession,
    date_from: str | None = None,
    date_to: str | None = None,
    vehicle_id: int | None = None,
) -> list[VehicleReportItem]:
    veh_query = select(Vehicle)
    if vehicle_id:
        veh_query = veh_query.where(Vehicle.id == vehicle_id)
    res_veh = await db.execute(veh_query)
    vehicles = res_veh.scalars().all()

    trips_query = (
        select(Trip)
        .options(selectinload(Trip.bookings), selectinload(Trip.vehicle))
        .where(Trip.status != TripStatus.CANCELLED)
    )
    if vehicle_id:
        trips_query = trips_query.where(Trip.vehicle_id == vehicle_id)

    res_trips = await db.execute(trips_query)
    all_trips = res_trips.scalars().all()

    filtered_trips = []
    for t in all_trips:
        t_date = _date_string(t.departure_time)
        if date_from and t_date < date_from:
            continue
        if date_to and t_date > date_to:
            continue
        filtered_trips.append(t)

    report_items = []
    for v in vehicles:
        v_trips = [t for t in filtered_trips if t.vehicle_id == v.id]
        
        cash_rev = 0.0
        card_rev = 0.0
        passengers_cnt = 0
        total_seats_capacity = sum(t.seats_limit_snapshot for t in v_trips)
        total_seated_passengers = 0

        for t in v_trips:
            for b in t.bookings:
                if b.status not in (BookingStatus.CANCELLED, BookingStatus.NOSHOW):
                    passengers_cnt += b.passengers_count
                    if b.booking_type == BookingType.SEATED:
                        total_seated_passengers += b.passengers_count
                    amt = _as_float(b.amount_paid)
                    pm = getattr(b, "payment_method", PaymentMethod.CASH)
                    if pm == PaymentMethod.CARD or str(pm) == "CARD":
                        card_rev += amt
                    else:
                        cash_rev += amt

        tot_rev = cash_rev + card_rev
        trips_cnt = len(v_trips)
        avg_rev = round(tot_rev / trips_cnt, 2) if trips_cnt > 0 else 0.0
        occupancy = round((total_seated_passengers / total_seats_capacity) * 100, 2) if total_seats_capacity > 0 else 0.0

        report_items.append(
            VehicleReportItem(
                vehicle_id=v.id,
                plate_number=v.plate_number,
                model=v.model,
                total_seats=v.total_seats,
                total_standing=v.total_standing,
                trips_count=trips_cnt,
                total_passengers=passengers_cnt,
                total_seats_capacity=total_seats_capacity,
                occupancy_rate=occupancy,
                cash_revenue=cash_rev,
                card_revenue=card_rev,
                total_revenue=tot_rev,
                avg_revenue_per_trip=avg_rev,
            )
        )

    return report_items


async def dashboard(db: AsyncSession) -> dict:
    return {
        "trips": await list_trips(db),
        "bookings": await list_bookings(db),
        "passengers": await list_passengers(db),
        "vehicles": await list_vehicles(db),
        "drivers": [user for user in await list_staff(db) if _role_value(user.role) == UserRole.DRIVER.value],
    }


async def refresh_user_stats(db: AsyncSession, user_id: int):
    stats_result = await db.execute(select(UserStats).where(UserStats.user_id == user_id))
    stats = stats_result.scalars().first()
    if not stats:
        stats = UserStats(user_id=user_id)
        db.add(stats)
        await db.flush()

    stmt = (
        select(Booking, Trip)
        .join(Trip, Booking.trip_id == Trip.id)
        .where(Booking.passenger_id == user_id)
        .order_by(Trip.departure_time.asc())
    )
    res = await db.execute(stmt)
    rows = res.all()

    boarded_count = 0
    noshow_count = 0
    early_cancellations = 0
    current_streak = 0
    neutralized_noshows = 0
    last_trip_dt = None

    for booking, trip in rows:
        if booking.status in (BookingStatus.BOARDED, BookingStatus.PAID):
            boarded_count += 1
            current_streak += 1
            if trip.departure_time:
                if last_trip_dt is None or trip.departure_time > last_trip_dt:
                    last_trip_dt = trip.departure_time
            if current_streak >= 5 and (noshow_count > neutralized_noshows):
                neutralized_noshows += 1
                current_streak = 0
        elif booking.status == BookingStatus.NOSHOW:
            noshow_count += 1
            current_streak = 0
        elif booking.status == BookingStatus.CANCELLED:
            if booking.created_at and trip.departure_time:
                dep_dt = trip.departure_time.replace(tzinfo=None)
                created_dt = booking.created_at.replace(tzinfo=None)
                diff = (dep_dt - created_dt).total_seconds()
                if diff >= 7200:
                    early_cancellations += 1

    effective_noshows = max(0, noshow_count - neutralized_noshows)
    base_score = 100 - (effective_noshows * 25)
    streak_bonus = min(boarded_count * 5, 40)
    early_cancel_bonus = early_cancellations * 2

    if boarded_count == 0 and noshow_count == 0:
        trust_score = 100
    else:
        trust_score = max(0, min(100, base_score + streak_bonus + early_cancel_bonus))

    stats.total_trips = boarded_count
    stats.total_noshows = noshow_count
    stats.trust_score_cached = trust_score
    stats.last_trip_date = last_trip_dt
    return stats


async def get_trip_manifest_use_case(
    db: AsyncSession, trip_id: int
) -> TripManifestDetailResponse:
    result = await db.execute(
        select(Trip)
        .where(Trip.id == trip_id)
        .options(
            selectinload(Trip.from_location),
            selectinload(Trip.to_location),
            selectinload(Trip.closed_by),
            selectinload(Trip.driver),
            selectinload(Trip.vehicle),
        )
    )
    trip = result.scalars().first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    passenger_alias = aliased(User)
    bookings_res = await db.execute(
        select(Booking, passenger_alias)
        .outerjoin(passenger_alias, Booking.passenger_id == passenger_alias.id)
        .where(Booking.trip_id == trip_id)
        .order_by(Booking.created_at.desc())
    )
    booking_rows = bookings_res.all()

    seated_count = 0
    standing_count = 0
    parcels_count = 0
    total_revenue = 0.0

    booking_responses = []
    for booking, passenger in booking_rows:
        resp = booking_to_admin(booking, passenger)
        booking_responses.append(resp)

        b_status = booking.status.name if hasattr(booking.status, 'name') else str(booking.status)
        if b_status not in ('CANCELLED', 'NOSHOW'):
            total_revenue += resp.amount_paid
            if booking.booking_type == BookingType.SEATED:
                seated_count += booking.passengers_count
            elif booking.booking_type == BookingType.STANDING:
                standing_count += booking.passengers_count
            elif booking.booking_type == BookingType.PARCEL:
                parcels_count += booking.passengers_count

    return TripManifestDetailResponse(
        trip=trip_to_admin(trip),
        seated_count=seated_count,
        seated_limit=trip.seats_limit_snapshot,
        standing_count=standing_count,
        standing_limit=trip.standing_limit_snapshot,
        parcels_count=parcels_count,
        total_revenue=total_revenue,
        bookings=booking_responses,
    )


async def create_manifest_booking_use_case(
    db: AsyncSession,
    trip_id: int,
    payload: AdminManifestBookingCreate,
    actor: User,
) -> AdminBookingResponse:
    if actor.role not in (UserRole.ADMIN, UserRole.DISPATCHER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dispatcher/Admin permissions required",
        )

    result = await db.execute(
        select(Trip).where(Trip.id == trip_id).with_for_update()
    )
    trip = result.scalars().first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    if trip.status in (TripStatus.COMPLETED, TripStatus.CLOSED, TripStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add booking to finalized trip",
        )

    phone_raw = re.sub(r"\D", "", payload.phone or "")
    if len(phone_raw) == 10 and phone_raw.startswith("0"):
        formatted_phone = f"+38{phone_raw}"
    elif len(phone_raw) == 12 and phone_raw.startswith("380"):
        formatted_phone = f"+{phone_raw}"
    else:
        formatted_phone = payload.phone

    passenger_result = await db.execute(select(User).where(User.phone.in_([formatted_phone, payload.phone])))
    passenger = passenger_result.scalars().first()
    if not passenger:
        passenger = User(
            phone=formatted_phone,
            full_name=payload.full_name or formatted_phone,
            role=UserRole.PASSENGER,
            is_active=True,
        )
        db.add(passenger)
        await db.flush()
    elif not passenger.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пасажир заблокований у системі",
        )
    elif payload.full_name and passenger.full_name != payload.full_name:
        passenger.full_name = payload.full_name

    if payload.booking_type == BookingType.SEATED:
        booked_res = await db.execute(
            select(func.sum(Booking.passengers_count)).where(
                Booking.trip_id == trip.id,
                Booking.booking_type == BookingType.SEATED,
                Booking.status.in_(ACTIVE_BOOKING_STATUSES),
            )
        )
        booked_seats = booked_res.scalar() or 0
        if trip.seats_limit_snapshot - booked_seats < payload.seats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Недостатньо вільних сидячих місць (вільно: {max(0, trip.seats_limit_snapshot - booked_seats)})",
            )
        unit_price = _as_float(trip.price_seated)
    elif payload.booking_type == BookingType.STANDING:
        booked_res = await db.execute(
            select(func.sum(Booking.passengers_count)).where(
                Booking.trip_id == trip.id,
                Booking.booking_type == BookingType.STANDING,
                Booking.status.in_(ACTIVE_BOOKING_STATUSES),
            )
        )
        booked_standing = booked_res.scalar() or 0
        if trip.standing_limit_snapshot - booked_standing < payload.seats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ліміт стоячих місць вичерпано (вільно: {max(0, trip.standing_limit_snapshot - booked_standing)})",
            )
        unit_price = _as_float(trip.price_standing)
    else:
        if trip.price_parcel is not None:
            unit_price = _as_float(trip.price_parcel)
        else:
            cfg = await _get_system_config(db)
            unit_price = _as_float(cfg.price_parcel)

    amount = unit_price * payload.seats

    booking = Booking(
        trip_id=trip.id,
        passenger_id=passenger.id,
        created_by_id=actor.id,
        booking_type=payload.booking_type,
        source=payload.source,
        status=BookingStatus.RESERVED,
        payment_method=getattr(payload, 'payment_method', PaymentMethod.CASH) or PaymentMethod.CASH,
        passengers_count=payload.seats,
        amount_paid=amount,
        comment=payload.comment,
    )
    db.add(booking)
    await db.flush()

    record_audit_log(
        db,
        actor,
        "BOOKING_CREATED",
        entity_type="booking",
        entity_id=booking.id,
        trip_id=trip.id,
        passenger_id=passenger.id,
        source=payload.source.value if hasattr(payload.source, 'value') else str(payload.source),
        message=f"Created {payload.booking_type.value} booking via {payload.source.value} for {passenger.phone}",
    )
    await db.commit()
    await manager.broadcast("BOOKING_MUTATED", {"trip_id": trip.id})
    await db.refresh(booking)
    return booking_to_admin(booking, passenger)


async def update_booking_status_use_case(
    db: AsyncSession,
    booking_id: int,
    new_status: BookingStatus,
    actor: User,
) -> AdminBookingResponse:
    if actor.role not in (UserRole.ADMIN, UserRole.DISPATCHER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dispatcher/Admin permissions required",
        )

    result = await db.execute(
        select(Booking).where(Booking.id == booking_id).with_for_update()
    )
    booking = result.scalars().first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    old_status = booking.status
    booking.status = new_status

    if booking.passenger_id:
        await refresh_user_stats(db, booking.passenger_id)

    record_audit_log(
        db,
        actor,
        "BOOKING_STATUS_UPDATED",
        entity_type="booking",
        entity_id=booking.id,
        trip_id=booking.trip_id,
        passenger_id=booking.passenger_id,
        message=f"Changed booking #{booking.id} status from {old_status.value} to {new_status.value}",
    )
    await db.commit()
    await manager.broadcast("BOOKING_MUTATED", {"trip_id": booking.trip_id})
    await db.refresh(booking)
    passenger = await db.get(User, booking.passenger_id) if booking.passenger_id else None
    return booking_to_admin(booking, passenger)


async def drivers_cash_reconciliation_use_case(
    db: AsyncSession,
    target_date: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    now_kyiv = datetime.now(KYIV_TZ)
    if date_from and date_to:
        try:
            d_from = datetime.strptime(date_from, "%Y-%m-%d").date()
            d_to = datetime.strptime(date_to, "%Y-%m-%d").date()
        except ValueError:
            d_from = now_kyiv.date()
            d_to = now_kyiv.date()
    elif target_date:
        try:
            d_from = datetime.strptime(target_date, "%Y-%m-%d").date()
            d_to = d_from
        except ValueError:
            d_from = now_kyiv.date()
            d_to = now_kyiv.date()
    else:
        d_from = now_kyiv.date()
        d_to = now_kyiv.date()

    if d_from > d_to:
        d_from, d_to = d_to, d_from

    drivers_stmt = (
        select(User)
        .where(User.role == UserRole.DRIVER)
        .order_by(User.full_name)
    )
    drivers = (await db.execute(drivers_stmt)).scalars().all()

    FromLoc = aliased(Location)
    ToLoc = aliased(Location)

    start_dt = datetime.combine(d_from, time.min, tzinfo=KYIV_TZ)
    end_dt = datetime.combine(d_to, time.max, tzinfo=KYIV_TZ)
    driver_summaries = []

    global_expected_revenue = 0.0
    global_submitted_cash = 0.0
    global_submitted_card = 0.0
    global_completed_trips = 0

    global_total_passengers = 0
    occupancy_rates = []
    routes_map = {}
    all_trips_perf = []

    # Chart aggregation map: label -> { revenue: 0.0, trips: 0, passengers: 0 }
    is_single_day = (d_from == d_to)
    chart_buckets = {}

    if is_single_day:
        for h in range(6, 23):
            label = f"{h:02d}:00"
            chart_buckets[label] = {"label": label, "revenue": 0.0, "trips": 0, "passengers": 0}
    else:
        curr = d_from
        while curr <= d_to:
            label = curr.strftime("%d.%m")
            chart_buckets[label] = {"label": label, "revenue": 0.0, "trips": 0, "passengers": 0}
            curr += timedelta(days=1)

    for driver in drivers:
        # Для контролю каси отримуємо ТІЛЬКИ ЗАВЕРШЕНІ та ЗАКРИТІ рейси (COMPLETED / CLOSED)
        trips_stmt = (
            select(Trip, FromLoc.name, ToLoc.name)
            .options(selectinload(Trip.closed_by))
            .join(FromLoc, Trip.from_location_id == FromLoc.id)
            .join(ToLoc, Trip.to_location_id == ToLoc.id)
            .where(Trip.driver_id == driver.id)
            .where(Trip.departure_time >= start_dt)
            .where(Trip.departure_time <= end_dt)
            .where(Trip.status.in_([TripStatus.COMPLETED, TripStatus.CLOSED]))
            .order_by(Trip.departure_time)
        )
        trips_rows = (await db.execute(trips_stmt)).all()

        total_trips_count = len(trips_rows)
        completed_trips_count = sum(1 for t, _, _ in trips_rows if t.status in (TripStatus.COMPLETED, TripStatus.CLOSED))
        closed_trips_count = sum(1 for t, _, _ in trips_rows if t.status == TripStatus.CLOSED)

        expected_total_sum = 0.0

        actual_submitted_cash = 0.0
        actual_submitted_card = 0.0

        closed_by_names = set()
        trip_details = []

        for trip, from_name, to_name in trips_rows:
            bookings_stmt = select(Booking).where(
                Booking.trip_id == trip.id,
                Booking.status.in_([BookingStatus.BOARDED, BookingStatus.PAID, BookingStatus.RESERVED])
            )
            bookings = (await db.execute(bookings_stmt)).scalars().all()

            t_expected = sum(float(b.amount_paid or 0) for b in bookings)
            expected_total_sum += t_expected

            t_passengers = sum(
                b.passengers_count for b in bookings 
                if (b.booking_type.name if hasattr(b.booking_type, 'name') else str(b.booking_type)).upper() in ('SEATED', 'STANDING')
            )
            global_total_passengers += t_passengers

            capacity = (trip.seats_limit_snapshot or 0) + (trip.standing_limit_snapshot or 0)
            occ_pct = min(100.0, round((t_passengers / capacity) * 100.0, 1)) if capacity > 0 else 0.0
            if capacity > 0:
                occupancy_rates.append(occ_pct)

            route_name = f"{from_name} → {to_name}"
            if route_name not in routes_map:
                routes_map[route_name] = {"route": route_name, "revenue": 0.0, "passengers": 0, "trips": 0, "occupancies": []}

            routes_map[route_name]["revenue"] += t_expected
            routes_map[route_name]["passengers"] += t_passengers
            routes_map[route_name]["trips"] += 1
            if capacity > 0:
                routes_map[route_name]["occupancies"].append(occ_pct)

            # Для зданої каси: якщо значення Null, то для фінансово закритого рейсу вважаємо 0.0
            t_cash = float(trip.submitted_cash) if trip.submitted_cash is not None else 0.0
            t_card = float(trip.submitted_card) if trip.submitted_card is not None else 0.0

            actual_submitted_cash += t_cash
            actual_submitted_card += t_card

            if trip.closed_by:
                closed_by_names.add(trip.closed_by.full_name)

            dep_kyiv = (trip.departure_time.replace(tzinfo=ZoneInfo("UTC")) if trip.departure_time.tzinfo is None else trip.departure_time).astimezone(KYIV_TZ)

            all_trips_perf.append({
                "trip_id": trip.id,
                "time": dep_kyiv.strftime("%H:%M"),
                "date": dep_kyiv.strftime("%d.%m.%Y"),
                "route": route_name,
                "driver_name": driver.full_name,
                "revenue": t_expected,
                "passengers": t_passengers,
                "capacity": capacity,
                "occupancy_pct": occ_pct,
                "status": trip.status.name,
            })

            # Chart bucket attribution
            if is_single_day:
                h_label = f"{dep_kyiv.hour:02d}:00"
                if h_label in chart_buckets:
                    chart_buckets[h_label]["revenue"] += t_expected
                    chart_buckets[h_label]["trips"] += 1
                    chart_buckets[h_label]["passengers"] += t_passengers
            else:
                d_label = dep_kyiv.strftime("%d.%m")
                if d_label in chart_buckets:
                    chart_buckets[d_label]["revenue"] += t_expected
                    chart_buckets[d_label]["trips"] += 1
                    chart_buckets[d_label]["passengers"] += t_passengers

            t_submitted_total = t_cash + t_card
            t_discrepancy = t_submitted_total - t_expected

            trip_details.append({
                "trip_id": trip.id,
                "time": dep_kyiv.strftime("%H:%M"),
                "date": dep_kyiv.strftime("%d.%m.%Y"),
                "route": f"{from_name} → {to_name}",
                "status": trip.status.name,
                "expected_revenue": t_expected,
                "submitted_cash": t_cash,
                "submitted_card": t_card,
                "total_submitted": t_submitted_total,
                "discrepancy": t_discrepancy,
            })

        total_submitted = actual_submitted_cash + actual_submitted_card
        discrepancy = total_submitted - expected_total_sum

        if completed_trips_count > 0 and closed_trips_count == completed_trips_count:
            rec_status = "CLOSED"
        elif completed_trips_count > 0:
            rec_status = "PENDING"
        elif total_trips_count > 0:
            rec_status = "SCHEDULED"
        else:
            rec_status = "NO_TRIPS"

        if total_trips_count > 0:
            global_expected_revenue += expected_total_sum
            global_submitted_cash += actual_submitted_cash
            global_submitted_card += actual_submitted_card
            global_completed_trips += completed_trips_count

            driver_summaries.append({
                "driver_id": driver.id,
                "driver_name": driver.full_name,
                "driver_phone": driver.phone or "—",
                "telegram_id": driver.telegram_id,
                "total_trips": total_trips_count,
                "completed_trips": completed_trips_count,
                "closed_trips": closed_trips_count,
                "expected_total": expected_total_sum,
                "submitted_cash": actual_submitted_cash,
                "submitted_card": actual_submitted_card,
                "total_submitted": total_submitted,
                "discrepancy": discrepancy,
                "status": rec_status,
                "closed_by": ", ".join(closed_by_names) if closed_by_names else None,
                "trips": trip_details,
            })

    date_str = d_from.strftime("%d.%m.%Y") if d_from == d_to else f"{d_from.strftime('%d.%m.%Y')} — {d_to.strftime('%d.%m.%Y')}"
    
    avg_occupancy = round(sum(occupancy_rates) / len(occupancy_rates), 1) if occupancy_rates else 0.0
    avg_revenue_per_trip = round(global_expected_revenue / global_completed_trips, 2) if global_completed_trips > 0 else 0.0

    routes_list = []
    for r_name, r_data in routes_map.items():
        avg_occ = round(sum(r_data["occupancies"]) / len(r_data["occupancies"]), 1) if r_data["occupancies"] else 0.0
        routes_list.append({
            "route": r_name,
            "revenue": r_data["revenue"],
            "passengers": r_data["passengers"],
            "trips": r_data["trips"],
            "avg_occupancy_rate": avg_occ,
        })

    routes_list.sort(key=lambda x: x["revenue"], reverse=True)
    top_trips = sorted(all_trips_perf, key=lambda x: x["revenue"], reverse=True)[:5]
    weak_trips = [t for t in sorted(all_trips_perf, key=lambda x: x["occupancy_pct"]) if t["occupancy_pct"] < 30.0][:5]

    return {
        "date": date_str,
        "date_from": d_from.strftime("%Y-%m-%d"),
        "date_to": d_to.strftime("%Y-%m-%d"),
        "raw_date": d_from.strftime("%Y-%m-%d"),
        "analytics": {
            "gross_revenue": global_expected_revenue,
            "completed_trips": global_completed_trips,
            "avg_revenue_per_trip": avg_revenue_per_trip,
            "total_passengers": global_total_passengers,
            "avg_occupancy_rate": avg_occupancy,
            "chart": list(chart_buckets.values()),
            "routes_comparison": routes_list,
            "top_trips": top_trips,
            "weak_trips": weak_trips,
        },
        "global": {
            "expected_revenue": global_expected_revenue,
            "submitted_cash": global_submitted_cash,
            "submitted_card": global_submitted_card,
            "total_submitted": global_submitted_cash + global_submitted_card,
            "discrepancy": (global_submitted_cash + global_submitted_card) - global_expected_revenue,
            "completed_trips": global_completed_trips,
            "active_drivers_count": len(driver_summaries),
        },
        "drivers": driver_summaries,
    }


async def confirm_driver_cash_use_case(
    db: AsyncSession,
    actor: User,
    driver_id: int,
    target_date: str,
    received_cash: float,
    received_card: float,
    comment: str | None = None,
) -> dict:
    if actor.role not in (UserRole.ADMIN, UserRole.DISPATCHER):
        raise HTTPException(status_code=403, detail="Лише Диспетчер або Адмін може підтверджувати здачу каси")

    try:
        filter_date = datetime.strptime(target_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Невірний формат дати (очікується YYYY-MM-DD)")

    driver = await db.get(User, driver_id)
    if not driver or driver.role != UserRole.DRIVER:
        raise HTTPException(status_code=404, detail="Водія не знайдено")

    start_dt = datetime.combine(filter_date, time.min, tzinfo=KYIV_TZ)
    end_dt = datetime.combine(filter_date, time.max, tzinfo=KYIV_TZ)

    trips_stmt = (
        select(Trip)
        .where(Trip.driver_id == driver_id)
        .where(Trip.departure_time >= start_dt)
        .where(Trip.departure_time <= end_dt)
        .where(Trip.status.in_([TripStatus.COMPLETED, TripStatus.CLOSED]))
        .with_for_update()
    )
    trips = (await db.execute(trips_stmt)).scalars().all()

    if not trips:
        raise HTTPException(status_code=400, detail=f"У водія {driver.full_name} немає завершених рейсів за {target_date}")

    count = len(trips)
    per_trip_cash = received_cash / count if count > 0 else 0.0
    per_trip_card = received_card / count if count > 0 else 0.0

    for trip in trips:
        trip.status = TripStatus.CLOSED
        trip.submitted_cash = per_trip_cash
        trip.submitted_card = per_trip_card
        trip.submitted_amount = per_trip_cash + per_trip_card
        trip.closed_by_id = actor.id
        trip.close_comment = comment or f"Касу підтверджено касиром {actor.full_name}"

    record_audit_log(
        db,
        actor,
        "DRIVER_CASH_CONFIRMED",
        entity_type="driver",
        entity_id=driver_id,
        message=f"Підтверджено касу водія {driver.full_name} за {target_date}: Готівка={received_cash}₴, Картка={received_card}₴. Прийняв: {actor.full_name}",
    )

    await db.commit()
    from app.websocket_manager import manager
    await manager.broadcast("CASH_CONFIRMED", {"driver_id": driver_id, "target_date": target_date})
    return await drivers_cash_reconciliation_use_case(db, target_date)


async def export_drivers_cash_csv(
    db: AsyncSession,
    date_from: str | None = None,
    date_to: str | None = None,
) -> str:
    res = await drivers_cash_reconciliation_use_case(db, date_from=date_from, date_to=date_to)
    drivers = res.get("drivers", [])

    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output, delimiter=';')

    writer.writerow([
        "Водій",
        "Телефон",
        "Всього рейсів",
        "Завершені рейси",
        "Закриті рейси",
        "Розрахункова каса (грн)",
        "Здано готівкою (грн)",
        "Оплачено на картку (грн)",
        "Всього здано (грн)",
        "Різниця / Відхилення (грн)",
        "Статус зведення",
        "Прийняв касир"
    ])

    for d in drivers:
        st_text = "Здано касиру" if d["status"] == "CLOSED" else ("Очікує здачі" if d["status"] == "PENDING" else "Немає завершених рейсів")
        writer.writerow([
            d["driver_name"],
            d["driver_phone"],
            d["total_trips"],
            d["completed_trips"],
            d["closed_trips"],
            d["expected_total"],
            d["submitted_cash"],
            d["submitted_card"],
            d["total_submitted"],
            d["discrepancy"],
            st_text,
            d["closed_by"] or "—"
        ])

    return output.getvalue()


async def export_trips_register_csv(
    db: AsyncSession,
    date_from: str | None = None,
    date_to: str | None = None,
) -> str:
    now_kyiv = datetime.now(KYIV_TZ)
    try:
        d_f = datetime.strptime(date_from, "%Y-%m-%d").date() if date_from else now_kyiv.date()
        d_t = datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else now_kyiv.date()
    except ValueError:
        d_f = now_kyiv.date()
        d_t = now_kyiv.date()

    if d_f > d_t:
        d_f, d_t = d_t, d_f

    start_dt = datetime.combine(d_f, time.min, tzinfo=KYIV_TZ)
    end_dt = datetime.combine(d_t, time.max, tzinfo=KYIV_TZ)

    FromLoc = aliased(Location)
    ToLoc = aliased(Location)

    stmt = (
        select(Trip, User, Vehicle, FromLoc.name, ToLoc.name)
        .options(selectinload(Trip.closed_by))
        .join(User, Trip.driver_id == User.id)
        .join(Vehicle, Trip.vehicle_id == Vehicle.id)
        .join(FromLoc, Trip.from_location_id == FromLoc.id)
        .join(ToLoc, Trip.to_location_id == ToLoc.id)
        .where(Trip.departure_time >= start_dt)
        .where(Trip.departure_time <= end_dt)
        .order_by(Trip.departure_time)
    )
    rows = (await db.execute(stmt)).all()

    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output, delimiter=';')

    writer.writerow([
        "Дата",
        "Час",
        "Маршрут",
        "Водій",
        "Автобус",
        "Номерний знак",
        "Статус рейсу",
        "Сидячих пасажирів",
        "Стоячих пасажирів",
        "Посилок",
        "Розрахункова каса (грн)",
        "Здана готівка (грн)",
        "Здана картка (грн)",
        "Прийняв касир"
    ])

    for trip, driver, vehicle, from_name, to_name in rows:
        bookings_stmt = select(Booking).where(
            Booking.trip_id == trip.id,
            Booking.status.in_([BookingStatus.BOARDED, BookingStatus.PAID, BookingStatus.RESERVED])
        )
        bookings = (await db.execute(bookings_stmt)).scalars().all()

        seated = sum(b.passengers_count for b in bookings if (b.booking_type.name if hasattr(b.booking_type, 'name') else str(b.booking_type)).upper() == 'SEATED')
        standing = sum(b.passengers_count for b in bookings if (b.booking_type.name if hasattr(b.booking_type, 'name') else str(b.booking_type)).upper() == 'STANDING')
        parcels = sum(1 for b in bookings if (b.booking_type.name if hasattr(b.booking_type, 'name') else str(b.booking_type)).upper() == 'PARCEL')
        expected_rev = sum(float(b.amount_paid or 0) for b in bookings)

        dep_kyiv = (trip.departure_time.replace(tzinfo=ZoneInfo("UTC")) if trip.departure_time.tzinfo is None else trip.departure_time).astimezone(KYIV_TZ)

        writer.writerow([
            dep_kyiv.strftime("%d.%m.%Y"),
            dep_kyiv.strftime("%H:%M"),
            f"{from_name} → {to_name}",
            driver.full_name,
            vehicle.model,
            vehicle.plate_number,
            trip.status.name,
            seated,
            standing,
            parcels,
            expected_rev,
            trip.submitted_cash if trip.submitted_cash is not None else expected_rev,
            trip.submitted_card if trip.submitted_card is not None else 0.0,
            trip.closed_by.full_name if trip.closed_by else "—"
        ])

    return output.getvalue()


async def export_parcels_register_csv(
    db: AsyncSession,
    date_from: str | None = None,
    date_to: str | None = None,
) -> str:
    now_kyiv = datetime.now(KYIV_TZ)
    try:
        d_f = datetime.strptime(date_from, "%Y-%m-%d").date() if date_from else now_kyiv.date()
        d_t = datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else now_kyiv.date()
    except ValueError:
        d_f = now_kyiv.date()
        d_t = now_kyiv.date()

    if d_f > d_t:
        d_f, d_t = d_t, d_f

    start_dt = datetime.combine(d_f, time.min, tzinfo=KYIV_TZ)
    end_dt = datetime.combine(d_t, time.max, tzinfo=KYIV_TZ)

    FromLoc = aliased(Location)
    ToLoc = aliased(Location)

    stmt = (
        select(Booking, Trip, User, FromLoc.name, ToLoc.name)
        .options(selectinload(Booking.passenger))
        .join(Trip, Booking.trip_id == Trip.id)
        .join(User, Trip.driver_id == User.id)
        .join(FromLoc, Trip.from_location_id == FromLoc.id)
        .join(ToLoc, Trip.to_location_id == ToLoc.id)
        .where(Booking.booking_type == BookingType.PARCEL)
        .where(Trip.departure_time >= start_dt)
        .where(Trip.departure_time <= end_dt)
        .where(Booking.status != BookingStatus.CANCELLED)
        .order_by(Trip.departure_time)
    )
    rows = (await db.execute(stmt)).all()

    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output, delimiter=';')

    writer.writerow([
        "Дата рейсу",
        "Час",
        "Маршрут",
        "Водій",
        "Відправник / Пасажир",
        "Телефон",
        "Джерело",
        "Сума до сплати (грн)",
        "Статус посилки",
        "Примітка"
    ])

    for booking, trip, driver, from_name, to_name in rows:
        dep_kyiv = (trip.departure_time.replace(tzinfo=ZoneInfo("UTC")) if trip.departure_time.tzinfo is None else trip.departure_time).astimezone(KYIV_TZ)
        p_name = booking.passenger.full_name if booking.passenger else "Невідомий"
        p_phone = booking.passenger.phone if booking.passenger else "—"

        writer.writerow([
            dep_kyiv.strftime("%d.%m.%Y"),
            dep_kyiv.strftime("%H:%M"),
            f"{from_name} → {to_name}",
            driver.full_name,
            p_name,
            p_phone,
            booking.source.name,
            booking.amount_paid or 0.0,
            booking.status.name,
            booking.comment or "—"
        ])

    return output.getvalue()


async def get_finance_closures_history_use_case(
    db: AsyncSession,
    limit: int = 50,
) -> list[dict]:
    stmt = (
        select(AuditLog, User)
        .outerjoin(User, AuditLog.actor_id == User.id)
        .where(AuditLog.action.in_(["DRIVER_CASH_CONFIRMED", "TRIP_CLOSED"]))
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()

    history = []
    for audit, actor in rows:
        created_kyiv = (audit.created_at.replace(tzinfo=ZoneInfo("UTC")) if audit.created_at.tzinfo is None else audit.created_at).astimezone(KYIV_TZ)
        history.append({
            "id": audit.id,
            "created_at": created_kyiv.strftime("%d.%m.%Y %H:%M:%S"),
            "action": audit.action,
            "actor_name": actor.full_name if actor else "Система",
            "actor_role": actor.role.name if actor else "SYSTEM",
            "message": audit.message or "",
            "entity_type": audit.entity_type,
            "entity_id": audit.entity_id,
            "trip_id": audit.trip_id,
        })

    return history


async def promote_waitlist_bookings_use_case(db: AsyncSession, trip_id: int) -> list[Booking]:
    """
    Перевіряє, чи вивільнилися місця на рейсі trip_id,
    і автоматично переводить найстаріші бронювання зі статусом WAITLIST
    у підтверджений статус RESERVED (спочатку сидячі, потім стоячі).
    """
    trip = await db.get(Trip, trip_id)
    if not trip or trip.status in (TripStatus.CANCELLED, TripStatus.CLOSED):
        return []

    # 1. Рахуємо вже зайняті місця
    booked_seated_stmt = (
        select(func.sum(Booking.passengers_count))
        .where(Booking.trip_id == trip_id)
        .where(Booking.booking_type == BookingType.SEATED)
        .where(Booking.status.in_([BookingStatus.RESERVED, BookingStatus.PAID, BookingStatus.BOARDED]))
    )
    booked_seated = (await db.execute(booked_seated_stmt)).scalar() or 0
    available_seats = max(0, trip.seats_limit_snapshot - booked_seated)

    booked_standing_stmt = (
        select(func.sum(Booking.passengers_count))
        .where(Booking.trip_id == trip_id)
        .where(Booking.booking_type == BookingType.STANDING)
        .where(Booking.status.in_([BookingStatus.RESERVED, BookingStatus.PAID, BookingStatus.BOARDED]))
    )
    booked_standing = (await db.execute(booked_standing_stmt)).scalar() or 0
    available_standing = max(0, (trip.standing_limit_snapshot or 0) - booked_standing)

    if available_seats <= 0 and available_standing <= 0:
        return []

    # 2. Беремо квитки зі статусом WAITLIST у порядку черги (created_at ASC)
    waitlist_stmt = (
        select(Booking)
        .where(Booking.trip_id == trip_id)
        .where(Booking.status == BookingStatus.WAITLIST)
        .order_by(Booking.created_at.asc())
        .with_for_update()
    )
    waitlist_bookings = (await db.execute(waitlist_stmt)).scalars().all()

    promoted: list[Booking] = []
    for w_booking in waitlist_bookings:
        needed = w_booking.passengers_count or 1
        if available_seats >= needed:
            w_booking.status = BookingStatus.RESERVED
            w_booking.booking_type = BookingType.SEATED
            w_booking.amount_paid = float(trip.price_seated) * needed
            available_seats -= needed
            promoted.append(w_booking)
        elif available_standing >= needed:
            w_booking.status = BookingStatus.RESERVED
            w_booking.booking_type = BookingType.STANDING
            w_booking.amount_paid = float(trip.price_standing) * needed
            available_standing -= needed
            promoted.append(w_booking)
        else:
            break

    if promoted:
        await db.commit()
        await manager.broadcast("BOOKING_MUTATED", {"trip_id": trip_id})

    return promoted


async def change_user_role(db: AsyncSession, user_id: int, new_role: UserRole, actor: User) -> AdminUserResponse:
    if actor.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Лише Головний Адміністратор має право змінювати ролі користувачів",
        )
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Користувача не знайдено")

    user.role = new_role
    await db.commit()
    await refresh_user_stats(db, user.id)
    await db.commit()
    await db.refresh(user)
    return user_to_admin(user)
