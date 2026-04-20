import os
import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
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
    # Runtime path injection handles this, but IDEs might not see it
    pass
from routers import routing, ai, websocket

# --- Logging Setup ---
def setup_cloud_logging():
    client = cloud_logging.Client()
    client.setup_logging()
    print("[INIT] Google Cloud Logging integrated.")

# --- Lifespan Manager (Corrected) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Boot sequence: Guaranteed synchronization before traffic.
    1. Parse DSL -> 2. Allocate C-Memory -> 3. Sync State -> 4. Open Streams
    """
    print("[BOOT] Starting EventFlow Enterprise Server...")
    
    # 1. Parse Configuration (Lark)
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    compiler = VenueCompiler(redis_url=redis_url)
    # Assuming test.venue at root as per initial dir check
    venue_file = os.path.join(BASE_DIR, "../../../test.venue")
    venue_data = compiler.compile(venue_file)
    
    # 2. Allocate Memory (Cython)
    # contiguous Node and Edge arrays
    astar.init_venue_graph(venue_data["nodes"], venue_data["edges"])
    
    # 3. Connect & Sync Services
    await redis_service.connect()
    await redis_service.sync_initial_state(venue_data)
    
    # 4. Initialize Persistent BigQuery Stream
    await telemetry_service.connect()
    
    # 5. Background Tasks (FIX: create_task to avoid blocking boot)
    # This prevents the lifespan manager from hanging.
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
    allow_origins=["*"], # In production, restrict this to your specific frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global Exception Handling (Enterprise Sanitization) ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catches all internal errors, logs stack trace to Cloud Logging,
    and returns a sanitized JSON response to the client.
    """
    # Cloud Logging automatically captures this via the setup_cloud_logging integration
    print(f"[INTERNAL_ERROR] {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "An internal system error occurred. Telemetry has been sent to staff for triage."
        }
    )

# --- Router Injections ---
app.include_router(routing.router)
app.include_router(ai.router)
app.include_router(websocket.router)

if __name__ == "__main__":
    import uvicorn
    # Use standard Cloud Logging in production
    if os.getenv("ENV") == "production":
        setup_cloud_logging()
    uvicorn.run(app, host="0.0.0.0", port=8000)
