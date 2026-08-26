import pytest
from starlette.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.websocket_manager import manager
from app.db.models import User, UserRole
from app.services.auth_service import create_access_token


@pytest.mark.asyncio
async def test_websocket_ping_pong_and_manager(db_session: AsyncSession):
    user = User(phone="+380970001122", full_name="WS User", role=UserRole.PASSENGER, is_active=True)
    db_session.add(user)
    await db_session.commit()

    client = TestClient(app)
    token = create_access_token(user.id, user.role)

    with client.websocket_connect(f"/ws?token={token}") as websocket:
        websocket.send_text("ping")
        data = websocket.receive_text()
        assert '{"event":"pong"}' in data


@pytest.mark.asyncio
async def test_websocket_manager_broadcast_and_disconnect():
    class DummyWebSocket:
        def __init__(self):
            self.sent = []

        async def accept(self):
            pass

        async def send_text(self, data: str):
            self.sent.append(data)

        async def send_json(self, data: dict):
            self.sent.append(data)

    dummy_ws = DummyWebSocket()
    await manager.connect(dummy_ws, telegram_id=500600)
    assert len(manager.active_connections) >= 1

    await manager.broadcast("TEST_EVENT", {"key": "value"})
    assert len(dummy_ws.sent) >= 1

    manager.disconnect(dummy_ws)
