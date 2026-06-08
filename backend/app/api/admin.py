from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import joinedload
from app.db.database import get_db
from app.db.models import User, Trip, Booking, Location, Vehicle, TripStatus, UserRole
from app.schemas.user import UserRead
from app.schemas.admin import AdminStats, TripAdminRead, TripCreate, VehicleRead, VehicleCreate
from typing import List
from datetime import datetime, date, timedelta
import logging

router = APIRouter(tags=["Admin"])

# --- STATISTICS ---
@router.get("/admin/stats", response_model=AdminStats)
async def get_admin_stats(db: AsyncSession = Depends(get_db)):
    users_count = await db.scalar(select(func.count(User.id)))
    trips_count = await db.scalar(select(func.count(Trip.id)))
    bookings_count = await db.scalar(select(func.count(Booking.id)))
    
    today = date.today()
    revenue_today = await db.scalar(
        select(func.sum(Booking.amount_paid))
        .join(Trip)
        .where(and_(
            func.date(Trip.departure_time) == today,
            Booking.status != "CANCELLED"
        ))
    ) or 0.0
    
    return {
        "users_total": users_count,
        "trips_total": trips_count,
        "bookings_total": bookings_count,
        "revenue_today": float(revenue_today),
    }

# --- TRIPS ---
@router.get("/admin/trips", response_model=List[TripAdminRead])
async def get_admin_trips(
    day_offset: int = 0, 
    route: str = "all", 
    status: str = "all",
    db: AsyncSession = Depends(get_db)
):
    target_date = date.today() + timedelta(days=day_offset)
    
    query = select(Trip).options(
        joinedload(Trip.driver),
        joinedload(Trip.vehicle),
        joinedload(Trip.from_location),
        joinedload(Trip.to_location)
    ).where(func.date(Trip.departure_time) == target_date)
    
    if status != "all":
        query = query.where(Trip.status == status)
        
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/admin/trips", response_model=TripAdminRead)
async def create_trip(trip_data: TripCreate, db: AsyncSession = Depends(get_db)):
    # Fetch vehicle to get seats snapshots
    vehicle = await db.get(Vehicle, trip_data.vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
        
    new_trip = Trip(
        **trip_data.model_dump(),
        seats_limit_snapshot=vehicle.total_seats,
        standing_limit_snapshot=vehicle.total_standing,
        status=TripStatus.SCHEDULED
    )
    db.add(new_trip)
    await db.commit()
    await db.refresh(new_trip)
    
    # Reload with relationships
    stmt = select(Trip).options(
        joinedload(Trip.driver),
        joinedload(Trip.vehicle),
        joinedload(Trip.from_location),
        joinedload(Trip.to_location)
    ).where(Trip.id == new_trip.id)
    result = await db.execute(stmt)
    return result.scalar_one()

@router.patch("/admin/trips/{trip_id}/status")
async def update_trip_status(trip_id: int, status: TripStatus, db: AsyncSession = Depends(get_db)):
    trip = await db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    trip.status = status
    await db.commit()
    return {"status": "success", "new_status": status}

# --- CRM / USERS ---
@router.get("/admin/users", response_model=List[UserRead])
async def get_admin_users(search: str = "", db: AsyncSession = Depends(get_db)):
    query = select(User).options(joinedload(User.stats))
    if search:
        query = query.where(or_(
            User.full_name.ilike(f"%{search}%"),
            User.phone.ilike(f"%{search}%")
        ))
    result = await db.execute(query)
    return result.scalars().all()

# --- VEHICLES ---
@router.get("/admin/vehicles", response_model=List[VehicleRead])
async def get_vehicles(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Vehicle))
    return result.scalars().all()

@router.post("/admin/vehicles", response_model=VehicleRead)
async def create_vehicle(vehicle_data: VehicleCreate, db: AsyncSession = Depends(get_db)):
    new_vehicle = Vehicle(**vehicle_data.model_dump())
    db.add(new_vehicle)
    await db.commit()
    await db.refresh(new_vehicle)
    return new_vehicle

# --- LOCATIONS ---
@router.get("/admin/locations")
async def get_locations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Location))
    return result.scalars().all()
