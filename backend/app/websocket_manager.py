import json
import logging
from typing import Any
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("websocket_manager")

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket, telegram_id: int | None = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected (tg_id={telegram_id}). Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Remaining connections: {len(self.active_connections)}")

    async def broadcast(self, event_type: str, data: dict[str, Any] | None = None):
        if not self.active_connections:
            return

        payload = {
            "event": event_type,
            "data": data or {},
        }
        message_str = json.dumps(payload, ensure_ascii=False)

        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.warning(f"Error sending websocket message: {e}")
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()
