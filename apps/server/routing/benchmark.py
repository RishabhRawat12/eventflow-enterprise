import time
import astar

def run_benchmark():
    node_count = 100
    edge_count = 100
    start_id = 0
    goal_id = 99
    
    print(f"Starting A* benchmark for {node_count} nodes...")
    
    # Warmup
    astar.run_astar_benchmark(start_id, goal_id, node_count, edge_count)
    
    iterations = 1000
    start_time = time.perf_counter()
    for _ in range(iterations):
        astar.run_astar_benchmark(start_id, goal_id, node_count, edge_count)
    end_time = time.perf_counter()
    
    total_time_ms = (end_time - start_time) * 1000
    avg_time_ms = total_time_ms / iterations
    
    print(f"Total time for {iterations} iterations: {total_time_ms:.4f} ms")
    print(f"Average execution time: {avg_time_ms:.4f} ms")
    
    if avg_time_ms < 1.0:
        print("Success: Execution time is sub-millisecond!")
    else:
        print("Warning: Execution time exceeds 1.0 ms.")

if __name__ == "__main__":
    run_benchmark()
