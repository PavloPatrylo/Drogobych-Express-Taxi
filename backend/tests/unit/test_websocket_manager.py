"""
Unit tests for ConnectionManager (WebSocket manager).
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.websocket_manager import ConnectionManager


@pytest.mark.asyncio
async def test_websocket_connect_and_disconnect():
    manager = ConnectionManager()
    ws_mock = AsyncMock()

    await manager.connect(ws_mock, telegram_id=12345)
    assert ws_mock in manager.active_connections
    ws_mock.accept.assert_called_once()

    manager.disconnect(ws_mock)
    assert ws_mock not in manager.active_connections


@pytest.mark.asyncio
async def test_websocket_broadcast_success():
    manager = ConnectionManager()
    ws1 = AsyncMock()
    ws2 = AsyncMock()

    await manager.connect(ws1)
    await manager.connect(ws2)

    await manager.broadcast("TEST_EVENT", {"key": "value"})

    expected_payload = json.dumps({"event": "TEST_EVENT", "data": {"key": "value"}}, ensure_ascii=False)
    ws1.send_text.assert_called_once_with(expected_payload)
    ws2.send_text.assert_called_once_with(expected_payload)
    assert len(manager.active_connections) == 2


@pytest.mark.asyncio
async def test_websocket_broadcast_handles_transmission_error():
    manager = ConnectionManager()
    ws_ok = AsyncMock()
    ws_broken = AsyncMock()
    ws_broken.send_text.side_effect = Exception("Connection closed abruptly")

    await manager.connect(ws_ok)
    await manager.connect(ws_broken)

    await manager.broadcast("FAIL_TEST", {"a": 1})

    # Broken connection should be automatically disconnected and removed
    assert ws_ok in manager.active_connections
    assert ws_broken not in manager.active_connections
    assert len(manager.active_connections) == 1
