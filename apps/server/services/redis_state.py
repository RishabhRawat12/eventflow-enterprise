import os
import asyncio
import json
import redis.asyncio as redis
from typing import Dict, Set

class RedisStateService:
    """
    Manages real-time venue state in Redis, handles Bloom filters (bit-fields),
    and orchestrates Pub/Sub broadcasting for WebSocket clients.
    """
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.client: Optional[redis.Redis] = None
        self.pubsub = None
        self._connected_clients: Set[asyncio.Queue] = set()
        self._listener_task = None

    async def connect(self):
        if self.redis_url == "mock-redis":
            import fakeredis.aioredis as fakeredis
            print("[REDIS] Running in MOCK mode (fakeredis).")
            self.client = fakeredis.FakeRedis(decode_responses=True)
        else:
            print(f"[REDIS] Connecting to {self.redis_url}")
            self.client = redis.from_url(self.redis_url, decode_responses=True)
        
        self.pubsub = self.client.pubsub()

    async def sync_initial_state(self, venue_data: dict):
        """
        Populates initial zone capacity and occupancy in Redis.
        Used during the lifespan boot sequence.
        """
        async with self.client.pipeline() as pipe:
            for zone in venue_data.get("zones", []):
                zone_id = zone["id"]
                key = f"venue:stadium:zone:{zone_id}"
                pipe.hset(key, mapping={
                    "capacity": zone["cap"],
                    "occupancy": 0,
                    "weight": 0.0
                })
            await pipe.execute()
        print(f"[REDIS] Initialized {len(venue_data.get('zones', []))} zones.")

    async def update_zone_weight(self, zone_id: int, weight: float):
        """
        Updates a zone's congestion weight and broadcasts to the Pub/Sub channel.
        """
        key = f"venue:stadium:zone:{zone_id}"
        await self.client.hset(key, "weight", weight)
        
        # Broadcast minified JSON for WebSocket consumption
        payload = {"z": zone_id, "w": round(weight, 2)}
        await self.client.publish("venue:stadium:updates", json.dumps(payload))

    async def start_pubsub_listener(self):
        """
        Listens to Redis Pub/Sub and pushes updates to connected WebSocket queues.
        This must be run as a background task.
        """
        await self.pubsub.subscribe("venue:stadium:updates")
        print("[REDIS] Pub/Sub listener active on 'venue:stadium:updates'")
        
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    # Distribute to all active WebSocket connections
                    for queue in self._connected_clients:
                        await queue.put(data)
        except asyncio.CancelledError:
            await self.pubsub.unsubscribe("venue:stadium:updates")
            print("[REDIS] Pub/Sub listener shut down.")

    def add_client(self, queue: asyncio.Queue):
        self._connected_clients.add(queue)

    def remove_client(self, queue: asyncio.Queue):
        self._connected_clients.discard(queue)

    async def disconnect(self):
        if self.client:
            await self.client.close()

# Singleton instance
redis_service = RedisStateService()
