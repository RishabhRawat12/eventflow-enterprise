from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from services.routing_engine import routing_engine
from middleware.auth import verify_firebase_token
import os

router = APIRouter(prefix="/api/v1/venue", tags=["venue"])

class ReloadRequest(BaseModel):
    venue_file: str = "test.venue"

@router.get("/")
async def get_venue_geometry(user: dict = Depends(verify_firebase_token)):
    """
    Exposes the current venue geometry (nodes, edges, configs).
    Used by the frontend to sync state after a RELOAD event.
    """
    if not routing_engine.compiler.stored_data:
        # Fallback to re-compiling if data is missing
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        venue_path = os.path.join(base_dir, "../../../test.venue")
        await routing_engine.reload_graph(venue_path)
        
    return routing_engine.compiler.stored_data

@router.post("/reload")
async def reload_venue(request: ReloadRequest, user: dict = Depends(verify_firebase_token)):
    """
    Triggers an atomic hot-reload of the venue graph.
    The RoutingEngine lock ensures this is safe even under high load.
    """
    # Resolve file path (assumed to be relative to project root or absolute)
    # For safety in this demo, we check a few likely locations
    possible_paths = [
        request.venue_file,
        os.path.join("../../", request.venue_file),
        os.path.join("../../../", request.venue_file)
    ]
    
    venue_path = None
    for p in possible_paths:
        if os.path.exists(p):
            venue_path = p
            break
            
    if not venue_path:
        # Fallback to the one used in main.py boot
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        venue_path = os.path.join(base_dir, "../../test.venue")
        if not os.path.exists(venue_path):
            raise HTTPException(status_code=404, detail=f"Venue file not found: {request.venue_file}")

    try:
        data = await routing_engine.reload_graph(venue_path)
        return {
            "status": "success",
            "message": "Atomic hot-reload successful",
            "nodes": data["nodes"],
            "edges": data["edges"],
            "configs": data["configs"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
