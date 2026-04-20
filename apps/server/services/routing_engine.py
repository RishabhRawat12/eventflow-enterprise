import threading
import os
import astar
from compiler import VenueCompiler
from services.redis_state import redis_service

class RoutingEngine:
    """
    Core routing engine that synchronizes access to the Cython A* memory blocks.
    Uses a global threading.Lock to prevent Use-After-Free during Hot-Reloads
    when called from FastAPI's background threadpool.
    """
    def __init__(self):
        self.lock = threading.Lock()
        self.compiler = VenueCompiler(redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        self.configs = {}

    def get_path(self, start_id: int, goal_id: int):
        """
        Calculates A* path distance under the protection of the lock.
        Releases the GIL within the Cython layer for true parallelism.
        """
        with self.lock:
            return astar.find_path(start_id, goal_id)

    def get_subgraph(self, start_id: int):
        """
        Extracts a sub-graph of depth N (from config) for AI context pruning.
        Executed in pure C++ via Cython to ensure bare-metal speed.
        """
        depth = int(self.configs.get("pruning_depth", 3))
        
        with self.lock:
            return astar.get_subgraph(start_id, depth)

    async def reload_graph(self, venue_file_path: str):
        """
        Performs an atomic hot-reload:
        1. Acquire threading lock (blocks all routing requests across all threads).
        2. Re-compile DSL.
        3. Release lock.
        """
        print(f"[RELOAD] Starting atomic swap for {venue_file_path}...")
        
        # We perform the compilation outside the lock if possible, 
        # but the astar.init_venue_graph (inside compile) needs the lock.
        # So we keep it within the lock for total atomicity.
        with self.lock:
            try:
                # 1. Compile (This internally calls astar.init_venue_graph)
                venue_data = self.compiler.compile(venue_file_path)
                self.configs = venue_data.get("configs", {})
                
                # 2. Sync to Redis
                await redis_service.sync_initial_state(venue_data)
                
                # 3. Broadcast RELOAD event to all WebSocket clients
                await redis_service.broadcast_system_event("RELOAD")
                
                print(f"[RELOAD] Atomic swap complete. New graph: {venue_data['nodes']} nodes, {venue_data['edges']} edges.")
                return venue_data
            except Exception as e:
                print(f"[RELOAD_ERROR] Swap failed: {e}")
                raise e

# Singleton Instance
routing_engine = RoutingEngine()
