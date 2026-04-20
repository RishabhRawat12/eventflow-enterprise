import time
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.telemetry import telemetry_service
import telemetry_pb2
from google.protobuf import timestamp_pb2

# The Cython module 'astar' will be imported from the path defined in build_all.py
import astar 

router = APIRouter(prefix="/api/v1")

class RouteRequest(BaseModel):
    start_id: int
    goal_id: int
    venue_id: str = "stadium_01"

@router.post("/route")
def get_path(request: RouteRequest):
    """
    Executes high-performance A* routing in Cython.
    Passes only primitive integers into the C extension to maintain zero overhead.
    """
    t0 = time.perf_counter()
    
    # 1. Core Cython Traversal (Synchronous/Nogil)
    # distance is -1.0 if no path exists
    distance = astar.find_path(request.start_id, request.goal_id)
    
    latency_ms = (time.perf_counter() - t0) * 1000

    # 2. Fire-and-forget Telemetry Streaming
    # Offloaded to a background task so it doesn't block the routing response
    ts = timestamp_pb2.Timestamp()
    ts.GetCurrentTime()
    
    telemetry_event = telemetry_pb2.TelemetryEvent(
        venue_id=request.venue_id,
        node_id=request.start_id,
        event_type="PATH_FINDING",
        latency_ms=latency_ms,
        timestamp=ts,
        metadata_json=f'{{"goal_id": {request.goal_id}, "distance": {distance}}}'
    )
    
    # Non-blocking telemetry dispatch
    asyncio.create_task(telemetry_service.stream_telemetry_event(telemetry_event))

    if distance < 0:
        raise HTTPException(status_code=404, detail="Path not reachable between selected nodes.")

    return {
        "status": "success",
        "distance": distance,
        "latency_ms": latency_ms,
        "origin": request.start_id,
        "destination": request.goal_id
    }
