from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket_manager import manager

router = APIRouter(tags=["WebSocket Real-Time"])

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, telegram_id: int | None = None):
    await manager.connect(websocket, telegram_id=telegram_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"event":"pong"}')
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
