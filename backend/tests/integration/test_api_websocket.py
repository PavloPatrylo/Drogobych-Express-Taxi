import pytest
from starlette.testclient import TestClient

from app.main import app
from app.websocket_manager import manager


def test_websocket_ping_pong_and_manager():
    client = TestClient(app)

    with client.websocket_connect("/ws?telegram_id=100200300") as websocket:
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
