from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_admin_access
from app.db.database import get_db
from app.db.models import User
from app.schemas.admin import AdminAuditLogResponse
from app.services import admin_use_cases

router = APIRouter(prefix="/audit", tags=["Admin Audit"])


@router.get("/log", response_model=list[AdminAuditLogResponse])
async def get_audit_log(
    limit: int = Query(100, ge=1, le=500),
    trip_id: int | None = None,
    passenger_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.list_audit_logs(
        db,
        limit=limit,
        trip_id=trip_id,
        passenger_id=passenger_id,
    )
