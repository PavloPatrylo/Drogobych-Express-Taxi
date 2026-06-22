from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_admin_access, check_owner_access
from app.db.database import get_db
from app.db.models import User, Vehicle
from app.schemas.admin import AdminVehicleResponse, VehicleCreate
from app.services import admin_use_cases

router = APIRouter(prefix="/vehicles", tags=["Admin Vehicles"])


@router.get("", response_model=list[AdminVehicleResponse])
@router.get("/", response_model=list[AdminVehicleResponse])
async def get_vehicles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.list_vehicles(db)


@router.post("", response_model=AdminVehicleResponse)
@router.post("/", response_model=AdminVehicleResponse)
async def create_vehicle(
    vehicle: VehicleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_owner_access),
):
    existing = await db.execute(select(Vehicle).where(Vehicle.plate_number == vehicle.plate_number))
    if existing.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vehicle plate already exists")

    new_vehicle = Vehicle(**vehicle.model_dump())
    db.add(new_vehicle)
    await db.commit()
    await db.refresh(new_vehicle)
    return admin_use_cases.vehicle_to_admin(new_vehicle)


@router.patch("/{vehicle_id}/toggle-active")
async def toggle_vehicle_status(
    vehicle_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_owner_access),
):
    vehicle = await db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    vehicle.is_active = not vehicle.is_active
    await db.commit()
    return {"message": "Vehicle status changed", "is_active": vehicle.is_active}
