from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from app.api.deps import get_ws_current_user
from app.db.models import User
from app.websocket_manager import manager

router = APIRouter(tags=["WebSocket Real-Time"])

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    current_user: User | None = Depends(get_ws_current_user)
):
    if not current_user:
        return

    await manager.connect(websocket, telegram_id=current_user.telegram_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"event":"pong"}')
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
