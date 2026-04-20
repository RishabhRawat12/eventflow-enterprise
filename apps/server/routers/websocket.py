from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from services.redis_state import redis_service
from middleware.auth import validate_token
import asyncio

router = APIRouter()

@router.websocket("/ws/venue/{venue_id}")
async def venue_websocket(websocket: WebSocket, venue_id: str, token: str = Query(...)):
    """
    Subscribes the client to real-time venue updates.
    Enforces Zero-Trust auth via query parameter.
    """
    try:
        await validate_token(token)
        await websocket.accept()
    except Exception:
        await websocket.close(code=4003)
        return
    
    # Each connection gets its own queue fed by the global Redis Pub/Sub listener
    queue = asyncio.Queue()
    redis_service.add_client(queue)
    
    try:
        # Keep connection open and push updates from the queue
        while True:
            update = await queue.get()
            await websocket.send_text(update)
    except WebSocketDisconnect:
        # Graceful cleanup
        redis_service.remove_client(queue)
        print(f"[WS] Client disconnected from {venue_id}")
    except Exception as e:
        print(f"[WS_ERROR] {e}")
        redis_service.remove_client(queue)
