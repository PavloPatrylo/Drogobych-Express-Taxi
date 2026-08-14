from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_admin_access
from app.db.database import get_db
from app.db.models import User
from app.schemas.admin import AdminCloseTripRequest, AdminTripResponse, ConfirmDriverCashRequest, DriverReportItem, VehicleReportItem
from app.services import admin_use_cases

router = APIRouter(prefix="/finance", tags=["Admin Finance"])


@router.get("/summary")
async def get_finance_summary(
    date_from: str | None = None,
    date_to: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.finance_summary(db, date_from, date_to)


@router.get("/reports/drivers", response_model=list[DriverReportItem])
async def get_drivers_report(
    date_from: str | None = None,
    date_to: str | None = None,
    driver_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.driver_report_use_case(
        db, date_from=date_from, date_to=date_to, driver_id=driver_id
    )


@router.get("/reports/vehicles", response_model=list[VehicleReportItem])
async def get_vehicles_report(
    date_from: str | None = None,
    date_to: str | None = None,
    vehicle_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.vehicle_report_use_case(
        db, date_from=date_from, date_to=date_to, vehicle_id=vehicle_id
    )


@router.get("/reconciliation")
async def get_drivers_reconciliation(
    target_date: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.drivers_cash_reconciliation_use_case(
        db, target_date=target_date, date_from=date_from, date_to=date_to
    )


@router.post("/confirm-driver-cash")
async def confirm_driver_cash(
    payload: ConfirmDriverCashRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.confirm_driver_cash_use_case(
        db,
        actor=current_user,
        driver_id=payload.driver_id,
        target_date=payload.target_date,
        received_cash=payload.received_cash,
        received_card=payload.received_card,
        comment=payload.comment,
    )


@router.get("/export/drivers-csv")
async def export_drivers_csv(
    date_from: str | None = None,
    date_to: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    csv_content = await admin_use_cases.export_drivers_cash_csv(db, date_from, date_to)
    filename = f"drivers_cash_report_{date_from or 'all'}_to_{date_to or 'all'}.csv"
    return Response(
        content=csv_content.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/trips-csv")
async def export_trips_csv(
    date_from: str | None = None,
    date_to: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    csv_content = await admin_use_cases.export_trips_register_csv(db, date_from, date_to)
    filename = f"trips_register_{date_from or 'all'}_to_{date_to or 'all'}.csv"
    return Response(
        content=csv_content.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/parcels-csv")
async def export_parcels_csv(
    date_from: str | None = None,
    date_to: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    csv_content = await admin_use_cases.export_parcels_register_csv(db, date_from, date_to)
    filename = f"parcels_register_{date_from or 'all'}_to_{date_to or 'all'}.csv"
    return Response(
        content=csv_content.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/trips/{trip_id}/stats")
async def get_trip_stats(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.trip_finance_stats(db, trip_id)


@router.get("/closures-history")
async def get_closures_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.get_finance_closures_history_use_case(db, limit=limit)


@router.post("/trips/{trip_id}/close", response_model=AdminTripResponse)
async def close_trip(
    trip_id: int,
    payload: AdminCloseTripRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.close_trip(db, trip_id, current_user, payload.submitted_amount)
