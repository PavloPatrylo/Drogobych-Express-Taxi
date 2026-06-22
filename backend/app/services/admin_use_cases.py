from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal

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
)
from app.schemas.admin import (
    AdminAuditLogResponse,
    AdminBookingResponse,
    AdminTripCreate,
    AdminTripUpdate,
    AdminTripResponse,
    AdminUserResponse,
    AdminVehicleResponse,
)

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


def _time_string(value: datetime | None) -> str | None:
    return value.strftime("%H:%M") if value else None


def _date_string(value: datetime) -> str:
    return value.date().isoformat()


def _combine_date_time(date_value: str, time_value: str | None) -> datetime | None:
    if not time_value:
        return None
    try:
        parsed_date = datetime.strptime(date_value, "%Y-%m-%d").date()
        parsed_time = time.fromisoformat(time_value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date or time") from exc
    return datetime.combine(parsed_date, parsed_time)


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
        submitted_amount=_as_float(trip.submitted_amount) if trip.submitted_amount is not None else None,
        closed_by_id=trip.closed_by_id,
        closed_by=trip.closed_by.full_name if trip.closed_by else None,
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
    return [user_to_admin(user) for user in result.scalars().all()]


async def list_trips(db: AsyncSession) -> list[AdminTripResponse]:
    result = await db.execute(
        select(Trip)
        .options(
            selectinload(Trip.from_location),
            selectinload(Trip.to_location),
            selectinload(Trip.closed_by),
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
        price_seated=payload.price_seated,
        price_standing=payload.price_standing,
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
    if actor and actor.role not in (UserRole.ADMIN, UserRole.DISPATCHER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dispatcher/Admin permissions required",
        )

    # SELECT ... FOR UPDATE (locks row to prevent race conditions)
    result = await db.execute(
        select(Trip)
        .where(Trip.id == trip_id)
        .options(selectinload(Trip.from_location), selectinload(Trip.to_location), selectinload(Trip.closed_by))
        .with_for_update()
    )
    trip = result.scalars().first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    previous_status = trip.status

    if new_status == TripStatus.CANCELLED:
        if trip.status in (TripStatus.COMPLETED, TripStatus.CLOSED, TripStatus.CANCELLED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trip already finalized",
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
        # If trip is CLOSED, we cannot change its status to anything
        if trip.status == TripStatus.CLOSED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change status of a closed trip",
            )
        valid_transitions = {
            TripStatus.SCHEDULED: TripStatus.BOARDING,
            TripStatus.BOARDING: TripStatus.ACTIVE,
            TripStatus.ACTIVE: TripStatus.COMPLETED,
        }
        if valid_transitions.get(trip.status) != new_status:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid trip status transition")
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
        "TRIP_STATUS_CHANGED",
        entity_type="trip",
        entity_id=trip.id,
        trip_id=trip.id,
        message=f"{previous_status.value} -> {new_status.value}",
    )
    await db.commit()
    await db.refresh(trip, attribute_names=["from_location", "to_location", "closed_by"])
    return trip_to_admin(trip)


async def close_trip(
    db: AsyncSession,
    trip_id: int,
    actor: User,
    submitted_amount: float | None = None,
) -> AdminTripResponse:
    if actor.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner role required",
        )

    # SELECT ... FOR UPDATE (locks row to prevent race conditions)
    result = await db.execute(
        select(Trip)
        .where(Trip.id == trip_id)
        .options(selectinload(Trip.from_location), selectinload(Trip.to_location), selectinload(Trip.closed_by))
        .with_for_update()
    )
    trip = result.scalars().first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    if trip.status not in (TripStatus.COMPLETED, TripStatus.CLOSED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only completed trips can be closed")

    trip.status = TripStatus.CLOSED
    trip.closed_by_id = actor.id
    trip.submitted_amount = submitted_amount

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
        "TRIP_CLOSED",
        entity_type="trip",
        entity_id=trip.id,
        trip_id=trip.id,
        message=f"Submitted amount: {submitted_amount}",
    )
    await db.commit()
    await db.refresh(trip, attribute_names=["from_location", "to_location", "closed_by"])
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
