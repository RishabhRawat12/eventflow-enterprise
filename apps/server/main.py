import os
import sys
import asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables from .env before service initialization
load_dotenv()

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google.cloud import logging as cloud_logging

# --- Path Initialization for Monorepo ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, "routing"))
sys.path.append(os.path.join(BASE_DIR, "../../packages/compiler/src"))

# Internal imports
from services.telemetry import telemetry_service
from services.redis_state import redis_service
try:
    from compiler import VenueCompiler # type: ignore
    import astar # type: ignore
except ImportError:
    pass
from routers import routing, ai, websocket, venue
from services.routing_engine import routing_engine
from middleware.auth import verify_firebase_token

# --- Logging Setup ---
def setup_cloud_logging():
    client = cloud_logging.Client()
    client.setup_logging()
    print("[INIT] Google Cloud Logging integrated.")

# --- Lifespan Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Boot sequence: Guaranteed synchronization before traffic.
    1. Connect & Sync Services
    2. Parse & Initialize Graph (Atomic)
    3. Start Background Listeners
    """
    # 1. Connect & Sync Services
    await redis_service.connect()
    await telemetry_service.connect()

    # 2. Parse & Initialize Graph (Atomic)
    venue_file = os.path.join(BASE_DIR, "../../../test.venue")
    await routing_engine.reload_graph(venue_file)
    
    # 3. Background Tasks
    redis_service._listener_task = asyncio.create_task(redis_service.start_pubsub_listener())
    
    print("[BOOT] Sequence Complete. Server is ready.")
    yield
    
    # Graceful Shutdown
    print("[SHUTDOWN] Cleaning up resources...")
    redis_service._listener_task.cancel()
    await telemetry_service.disconnect()
    await redis_service.disconnect()

app = FastAPI(title="EventFlow Enterprise", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global Exception Handling ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"[INTERNAL_ERROR] {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "An internal system error occurred."
        }
    )

# --- Router Injections (Hardened) ---
app.include_router(routing.router, dependencies=[Depends(verify_firebase_token)])
app.include_router(ai.router, dependencies=[Depends(verify_firebase_token)])
app.include_router(venue.router, dependencies=[Depends(verify_firebase_token)])
app.include_router(websocket.router)

if __name__ == "__main__":
    import uvicorn
    if os.getenv("ENV") == "production":
        setup_cloud_logging()
    uvicorn.run(app, host="0.0.0.0", port=8000)
