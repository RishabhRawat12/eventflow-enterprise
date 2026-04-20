import os
import redis
from lark import Lark, Transformer
# Note: astar would be imported after compilation in a real environment
# For the purpose of the script, we assume astar is available in the same package/path
import astar # type: ignore

class VenueCompiler:
    def __init__(self, redis_url="redis://localhost:6379"):
        # Load grammar from adjacent file
        grammar_path = os.path.join(os.path.dirname(__file__), "venue.lark")
        with open(grammar_path, "r") as f:
            self.parser = Lark(f.read(), parser='lalr')
        
        if redis_url == "mock-redis":
            import fakeredis
            print("[COMPILER] Using MOCK redis client.")
            self.redis_client = fakeredis.FakeRedis(decode_responses=True)
        else:
            self.redis_client = redis.from_url(redis_url)
        self.symbol_table = {}
        self.node_count = 0
        self.edge_count = 0
        self.zones = []
        self.edges = []

    def compile(self, file_path):
        with open(file_path, "r") as f:
            tree = self.parser.parse(f.read())
        
        # --- Pass 1: Discovery & Indexing ---
        self._pass1_indexing(tree)
        
        # --- Memory Allocation Bridge ---
        astar.init_venue_graph(self.node_count, self.edge_count)
        
        # --- Pass 2: Population ---
        self._pass2_population()
        
        # --- Atomic Redis Sync ---
        self._sync_to_redis()
        
        return {
            "nodes": self.node_count,
            "edges": self.edge_count,
            "zones": self.zones,
            "status": "Success"
        }

    def _pass1_indexing(self, tree):
        # Reset counters
        self.symbol_table = {}
        self.node_count = 0
        self.edge_count = 0
        self.zones = []
        self.edges = []

        # Find all zone definitions
        for node in tree.find_data("zone_def"):
            name = node.children[0].strip('"')
            if name not in self.symbol_table:
                self.symbol_table[name] = self.node_count
                self.node_count += 1
                
                # Gather properties for Pass 2
                self.zones.append({
                    "name": name,
                    "cap": int(node.children[1]),
                    "lat": float(node.children[2]),
                    "lon": float(node.children[3]),
                    "id": self.symbol_table[name]
                })

        # Find all edge definitions
        for node in tree.find_data("edge_def"):
            src = node.children[0].strip('"')
            target = node.children[1].strip('"')
            
            if src not in self.symbol_table or target not in self.symbol_table:
                raise ValueError(f"Edge references undefined zone: {src} -> {target}")
            
            self.edges.append({
                "source": src,
                "target": target,
                "weight": float(node.children[2]),
                "flow": node.children[3].strip('"')
            })
            self.edge_count += 1

    def _pass2_population(self):
        # 1. Populate Nodes
        # In our contiguous layout, edges are packed. 
        # We need to map edges to their source node starting indices.
        current_edge_idx = 0
        node_edge_map = {} # Maps node_id to (start_idx, count)
        
        for node_id in range(self.node_count):
            node_name = [name for name, idx in self.symbol_table.items() if idx == node_id][0]
            node_edges = [e for e in self.edges if e["source"] == node_name]
            
            # Record edge layout for this node
            node_edge_map[node_id] = (current_edge_idx, len(node_edges))
            
            # Map node to C-struct
            zone_data = [z for z in self.zones if z["name"] == node_name][0]
            astar.set_node(
                node_id, 
                node_id, 
                zone_data["lat"], 
                zone_data["lon"], 
                current_edge_idx, 
                len(node_edges),
                zone_data["cap"]
            )
            
            # 2. Populate Edges for this node
            for e in node_edges:
                target_id = self.symbol_table[e["target"]]
                # For baseline, dist is calculated or static from weight
                astar.set_edge(current_edge_idx, target_id, e["weight"], 0.0)
                current_edge_idx += 1

    def _sync_to_redis(self):
        pipeline = self.redis_client.pipeline()
        
        # Flush old venue data (assuming venue_id "stadium_01")
        pipeline.delete("venue:stadium_01:zones")
        pipeline.delete("venue:stadium_01:graph")
        
        # Load zone metadata and initial capacity
        for zone in self.zones:
            node_id = self.symbol_table[zone["name"]]
            pipeline.hset(f"venue:stadium_01:zone:{node_id}", mapping={
                "name": zone["name"],
                "capacity": zone["cap"],
                "occupancy": 0,
                "id": node_id
            })
            pipeline.sadd("venue:stadium_01:zones", node_id)
            
        pipeline.execute()
