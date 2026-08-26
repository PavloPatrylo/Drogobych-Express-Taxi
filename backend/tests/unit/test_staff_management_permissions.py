import pytest
from fastapi import HTTPException

from app.api.admin.auth import ensure_staff_management_permission
from app.db.models import User, UserRole


def test_dispatcher_cannot_manage_staff_accounts():
    dispatcher = User(role=UserRole.DISPATCHER)

    with pytest.raises(HTTPException) as exc_info:
        ensure_staff_management_permission(dispatcher, UserRole.DRIVER)

    assert exc_info.value.status_code == 403


def test_admin_can_manage_all_staff_roles():
    admin = User(role=UserRole.ADMIN)

    for role in UserRole:
        ensure_staff_management_permission(admin, role)
