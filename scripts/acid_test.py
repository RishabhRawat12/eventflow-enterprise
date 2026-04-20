import asyncio
import httpx
import time
import random
import sys
import argparse

async def run_worker(semaphore, worker_id, base_url, token):
    async with semaphore:
        headers = {"X-Internal-Load-Token": token}
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
        try:
            async with httpx.AsyncClient(timeout=10.0, headers=headers, limits=limits) as client:
                print(f"[WORKER {worker_id}] Online.")
                # Run for a long duration (120 seconds) for the demo
                end_time = time.time() + 120
                while time.time() < end_time:
                    try:
                        start_id = random.randint(0, 3)
                        goal_id = random.randint(0, 3)
                        resp = await client.post(f"{base_url}/api/v1/route", json={
                            "start_id": start_id,
                            "goal_id": goal_id
                        })
                        if resp.status_code != 200:
                            print(f"[WORKER {worker_id}] Error {resp.status_code}")
                    except Exception as e:
                        print(f"[WORKER {worker_id}] Connection Error: {e}")
                        await asyncio.sleep(2)
                    
                    await asyncio.sleep(random.uniform(0.5, 2.0))
        except Exception as e:
            print(f"[WORKER {worker_id}] Failed to start: {e}")

async def run_load_test(workers_count, url, token):
    print(f"[TEST] Starting Enterprise Acid Test with {workers_count} concurrent workers...")
    
    # Strictly control concurrency to avoid OS socket exhaustion
    # Windows typically allows ~500 concurrent sockets per process without tuning
    semaphore = asyncio.Semaphore(200) 
    
    tasks = [asyncio.create_task(run_worker(semaphore, i, url, token)) for i in range(workers_count)]
    
    print(f"[TEST] Dispatching workers... (This may take a moment to ramp up)")
    await asyncio.gather(*tasks)
    print(f"[TEST] Acid Test Complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=1000)
    parser.add_argument("--url", type=str, default="http://localhost:8000")
    parser.add_argument("--token", type=str, required=True)
    args = parser.parse_args()

    try:
        asyncio.run(run_load_test(args.workers, args.url, args.token))
    except KeyboardInterrupt:
        print("\n[TEST] Graceful shutdown.")
