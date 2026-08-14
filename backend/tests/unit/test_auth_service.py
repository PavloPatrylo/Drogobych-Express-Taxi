"""
Unit tests for authentication service (create_access_token, authenticate_user, get_staff_list).
"""
import pytest
from jose import jwt
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserRole
from app.core.config import settings
from app.core.security import hash_password
from app.services.auth_service import create_access_token, authenticate_user, get_staff_list


def test_create_access_token():
    user_id = 42
    role = UserRole.ADMIN

    token = create_access_token(user_id=user_id, role=role)
    assert isinstance(token, str)

    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    assert payload["sub"] == "42"
    assert payload["role"] == UserRole.ADMIN.value
    assert "exp" in payload


@pytest.mark.asyncio
async def test_authenticate_user_success(db_session: AsyncSession):
    hashed_pwd = hash_password("ValidPassword123")
    user = User(
        phone="+380971002001",
        full_name="Диспетчер Тест",
        password=hashed_pwd,
        role=UserRole.DISPATCHER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    authenticated = await authenticate_user(db_session, "+380971002001", "ValidPassword123")
    assert authenticated.id == user.id
    assert authenticated.role == UserRole.DISPATCHER


@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(db_session: AsyncSession):
    hashed_pwd = hash_password("ValidPassword123")
    user = User(
        phone="+380971002002",
        full_name="Адмін Тест",
        password=hashed_pwd,
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await authenticate_user(db_session, "+380971002002", "WrongPass")

    assert exc_info.value.status_code == 401
    assert "Невірні облікові дані" in exc_info.value.detail


@pytest.mark.asyncio
async def test_authenticate_user_inactive_account(db_session: AsyncSession):
    hashed_pwd = hash_password("ValidPassword123")
    user = User(
        phone="+380971002003",
        full_name="Заблокований Адмін",
        password=hashed_pwd,
        role=UserRole.ADMIN,
        is_active=False,
    )
    db_session.add(user)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await authenticate_user(db_session, "+380971002003", "ValidPassword123")

    assert exc_info.value.status_code == 403
    assert "заблоковано" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_authenticate_user_forbidden_role(db_session: AsyncSession):
    hashed_pwd = hash_password("ValidPassword123")
    passenger = User(
        phone="+380971002004",
        full_name="Освичений Пасажир",
        password=hashed_pwd,
        role=UserRole.PASSENGER,
        is_active=True,
    )
    db_session.add(passenger)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await authenticate_user(db_session, "+380971002004", "ValidPassword123")

    assert exc_info.value.status_code == 403
    assert "заборонено" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_staff_list(db_session: AsyncSession):
    driver = User(phone="+380971002010", full_name="Водій 1", role=UserRole.DRIVER, is_active=True)
    dispatcher = User(phone="+380971002011", full_name="Диспетчер 1", role=UserRole.DISPATCHER, is_active=True)
    passenger = User(phone="+380971002012", full_name="Пасажир 1", role=UserRole.PASSENGER, is_active=True)

    db_session.add_all([driver, dispatcher, passenger])
    await db_session.commit()

    staff = await get_staff_list(db_session)
    staff_ids = {s.id for s in staff}

    assert driver.id in staff_ids
    assert dispatcher.id in staff_ids
    assert passenger.id not in staff_ids
