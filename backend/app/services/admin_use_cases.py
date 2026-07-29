from __future__ import annotations

from datetime import datetime, time
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
)
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
        config = SystemConfig(id=1, price_seated=120.00, price_standing=80.00, price_parcel=50.00)
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
    stats = getattr(user, "stats", None)
    total_trips = stats.total_trips if stats else 0
    total_noshows = stats.total_noshows if stats else 0
    trust_score = stats.trust_score_cached if stats else max(0, round(100 - (total_noshows / max(total_trips, 1)) * 100))
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
    )


def trip_to_admin(trip: Trip) -> AdminTripResponse:
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
        price_parcel=_as_float(getattr(trip, 'price_parcel', 100.0) or 100.0),
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
    )


def booking_to_admin(booking: Booking, passenger: User | None = None) -> AdminBookingResponse:
    return AdminBookingResponse(
        id=booking.id,
        trip_id=booking.trip_id,
        passenger_id=booking.passenger_id,
        created_by_id=booking.created_by_id,
        booking_type=booking.booking_type,
        source=booking.source,
        status=booking.status,
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

    # If vehicle changed, update snapshot limits
    if trip.vehicle_id != vehicle.id:
        trip.seats_limit_snapshot = vehicle.total_seats
        trip.standing_limit_snapshot = vehicle.total_standing

    trip.driver_id = driver.id
    trip.vehicle_id = vehicle.id
    trip.from_location_id = from_location.id
    trip.to_location_id = to_location.id
    trip.departure_time = departure
    trip.arrival_time = arrival
    trip.price_seated = payload.price_seated
    trip.price_standing = payload.price_standing

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
        )
        .with_for_update()
    )
    trip = result.scalars().first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    previous_status = trip.status

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
        bookings = await db.execute(
            select(Booking).where(
                Booking.trip_id == trip.id,
                Booking.status.in_([BookingStatus.RESERVED, BookingStatus.PAID]),
            )
        )
        for booking in bookings.scalars().all():
            booking.status = BookingStatus.CANCELLED
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

    passenger_result = await db.execute(select(User).where(User.phone == phone))
    passenger = passenger_result.scalars().first()
    if not passenger:
        passenger = User(phone=phone, full_name=full_name or phone, role=UserRole.PASSENGER, is_active=True)
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

    booking = Booking(
        trip_id=trip.id,
        passenger_id=passenger.id,
        created_by_id=actor.id,
        booking_type=BookingType.SEATED,
        source=source,
        status=BookingStatus.RESERVED,
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
    return {
        "seated": sum(b.passengers_count for b in billable if b.booking_type == BookingType.SEATED),
        "standing": sum(b.passengers_count for b in billable if b.booking_type == BookingType.STANDING),
        "parcels": sum(b.passengers_count for b in billable if b.booking_type == BookingType.PARCEL),
        "revenue": sum(_as_float(b.amount_paid) for b in billable),
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
    bookings = [b for b in bookings if b.trip_id in filtered_trip_ids]

    total_revenue = sum(
        booking.amount_paid
        for booking in bookings
        if booking.status not in (BookingStatus.CANCELLED, BookingStatus.NOSHOW)
    )
    return {
        "total_revenue": total_revenue,
        "pending_close": [trip for trip in trips if trip.status == TripStatus.COMPLETED],
        "closed_trips": [trip for trip in trips if trip.status == TripStatus.CLOSED],
    }


async def dashboard(db: AsyncSession) -> dict:
    return {
        "trips": await list_trips(db),
        "bookings": await list_bookings(db),
        "passengers": await list_passengers(db),
        "vehicles": await list_vehicles(db),
        "drivers": [user for user in await list_staff(db) if _role_value(user.role) == UserRole.DRIVER.value],
    }


async def refresh_user_stats(db: AsyncSession, user_id: int):
    # 1. Ensure UserStats exists for this user
    stats_result = await db.execute(select(UserStats).where(UserStats.user_id == user_id))
    stats = stats_result.scalars().first()
    if not stats:
        stats = UserStats(user_id=user_id)
        db.add(stats)
        await db.flush()

    # 2. Count boarded bookings (total completed trips)
    boarded_stmt = select(func.count(Booking.id)).where(
        Booking.passenger_id == user_id,
        Booking.status == BookingStatus.BOARDED
    )
    boarded_count = (await db.execute(boarded_stmt)).scalar() or 0

    # 3. Count noshow bookings
    noshow_stmt = select(func.count(Booking.id)).where(
        Booking.passenger_id == user_id,
        Booking.status == BookingStatus.NOSHOW
    )
    noshow_count = (await db.execute(noshow_stmt)).scalar() or 0

    # 4. Update stats and trust score cached
    stats.total_trips = boarded_count
    stats.total_noshows = noshow_count
    total_relevant = boarded_count + noshow_count
    if total_relevant > 0:
        stats.trust_score_cached = max(0, round(100 - (noshow_count / total_relevant) * 100))
    else:
        stats.trust_score_cached = 100


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

        if booking.status != BookingStatus.CANCELLED:
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

    passenger_result = await db.execute(select(User).where(User.phone == payload.phone))
    passenger = passenger_result.scalars().first()
    if not passenger:
        passenger = User(
            phone=payload.phone,
            full_name=payload.full_name or payload.phone,
            role=UserRole.PASSENGER,
            is_active=True,
        )
        db.add(passenger)
        await db.flush()
    elif payload.full_name and passenger.full_name != payload.full_name:
        passenger.full_name = payload.full_name

    if payload.booking_type == BookingType.SEATED:
        unit_price = _as_float(trip.price_seated)
    elif payload.booking_type == BookingType.STANDING:
        unit_price = _as_float(trip.price_standing)
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
    await db.refresh(booking)
    passenger = await db.get(User, booking.passenger_id) if booking.passenger_id else None
    return booking_to_admin(booking, passenger)
    stats.trust_score_cached = max(0, round(100 - (noshow_count / max(boarded_count, 1)) * 100))
    await db.flush()
