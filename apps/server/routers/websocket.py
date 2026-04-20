from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.redis_state import redis_service
import asyncio

router = APIRouter()

@router.websocket("/ws/venue/{venue_id}")
async def venue_websocket(websocket: WebSocket, venue_id: str):
    """
    Subscribes the client to real-time venue updates.
    Payloads are minified JSON (e.g. {"z": 14, "w": 5.2}) to minimize overhead.
    """
    await websocket.accept()
    
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
