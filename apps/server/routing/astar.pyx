# cython: language_level=3
# distutils: language = c++

from libc.stdlib cimport malloc, free
from libc.math cimport sqrt

from libcpp cimport bool

cdef extern from "pq.h":
    struct PQElement:
        unsigned int node_id
        float f_score
    
    cppclass MinPriorityQueue:
        MinPriorityQueue() except +
        void push(PQElement) nogil
        PQElement top() nogil
        void pop() nogil
        bool empty() nogil

cdef struct Edge:
    unsigned int target_id
    float static_distance
    float dynamic_congestion_weight

cdef struct Node:
    unsigned int id
    float lat
    float lon
    unsigned int edge_start_idx
    unsigned int edge_count
    unsigned int current_occupancy
    unsigned int max_capacity

cdef struct VenueGraph:
    Node* nodes        # Array of all nodes
    unsigned int node_count
    Edge* edges        # Flat array of all edges
    unsigned int edge_count

from cpython.mem cimport PyMem_Malloc, PyMem_Free

cdef VenueGraph _global_graph

# Initialization functions for the compiler bridge
cpdef init_venue_graph(unsigned int node_count, unsigned int edge_count):
    global _global_graph
    # Cleanup old graph if exists
    if _global_graph.nodes != NULL:
        PyMem_Free(_global_graph.nodes)
    if _global_graph.edges != NULL:
        PyMem_Free(_global_graph.edges)
    
    _global_graph.node_count = node_count
    _global_graph.edge_count = edge_count
    _global_graph.nodes = <Node*>PyMem_Malloc(node_count * sizeof(Node))
    _global_graph.edges = <Edge*>PyMem_Malloc(edge_count * sizeof(Edge))
    
    if not _global_graph.nodes or not _global_graph.edges:
        raise MemoryError("Failed to allocate VenueGraph memory blocks.")

cpdef set_node(unsigned int idx, unsigned int id, float lat, float lon, unsigned int start_idx, unsigned int count, unsigned int cap):
    global _global_graph
    _global_graph.nodes[idx].id = id
    _global_graph.nodes[idx].lat = lat
    _global_graph.nodes[idx].lon = lon
    _global_graph.nodes[idx].edge_start_idx = start_idx
    _global_graph.nodes[idx].edge_count = count
    _global_graph.nodes[idx].max_capacity = cap
    _global_graph.nodes[idx].current_occupancy = 0

cpdef set_edge(unsigned int idx, unsigned int target_id, float dist, float weight):
    global _global_graph
    _global_graph.edges[idx].target_id = target_id
    _global_graph.edges[idx].static_distance = dist
    _global_graph.edges[idx].dynamic_congestion_weight = weight

# Python-safe wrapper for the A* engine
cpdef print_graph():
    global _global_graph
    cdef unsigned int i, j
    cdef Node* n
    cdef Edge* e
    
    print(f"\n[Cython] VenueGraph Memory State:")
    print(f"Nodes: {_global_graph.node_count}, Edges: {_global_graph.edge_count}")
    
    for i in range(_global_graph.node_count):
        n = &_global_graph.nodes[i]
        print(f" NODE {i}: id={n.id}, lat={n.lat:.4f}, lon={n.lon:.4f}, "
              f"edges=[{n.edge_start_idx}:{n.edge_start_idx + n.edge_count}], cap={n.max_capacity}")
        
        for j in range(n.edge_start_idx, n.edge_start_idx + n.edge_count):
            e = &_global_graph.edges[j]
            print(f"   -> EDGE {j}: target_id={e.target_id}, dist={e.static_distance:.2f}, "
                  f"weight={e.dynamic_congestion_weight:.2f}")

cpdef find_path(unsigned int start_id, unsigned int goal_id):
    cdef float result
    with nogil:
        result = _astar_internal(&_global_graph, start_id, goal_id)
    return result

cpdef run_astar_benchmark(unsigned int start_id, unsigned int goal_id, unsigned int node_count, unsigned int edge_count):
    """
    Python wrapper for the internal nogil A* implementation.
    Allocates a dummy graph for benchmarking as requested.
    """
    cdef VenueGraph graph
    graph.node_count = node_count
    graph.edge_count = edge_count
    graph.nodes = <Node*>malloc(node_count * sizeof(Node))
    graph.edges = <Edge*>malloc(edge_count * sizeof(Edge))
    
    # Initialize dummy linear graph
    cdef unsigned int i
    for i in range(node_count):
        graph.nodes[i].id = i
        graph.nodes[i].lat = 34.0520 + (i * 0.0001)
        graph.nodes[i].lon = -118.2430 + (i * 0.0001)
        graph.nodes[i].edge_start_idx = i
        graph.nodes[i].edge_count = 1 if i < node_count - 1 else 0
        if i < node_count - 1:
            graph.edges[i].target_id = i + 1
            graph.edges[i].static_distance = 10.0
            graph.edges[i].dynamic_congestion_weight = 0.0

    cdef float result
    with nogil:
        result = _astar_internal(&graph, start_id, goal_id)
    
    free(graph.nodes)
    free(graph.edges)
    return result

cdef float haversine_heuristic(float lat1, float lon1, float lat2, float lon2) noexcept nogil:
    cdef float dlat = lat2 - lat1
    cdef float dlon = lon2 - lon1
    cdef float dist_sq = (dlat * dlat) + (dlon * dlon)
    return <float>(sqrt(<double>dist_sq) * 111139.0)

cdef float get_edge_weight(Edge* edge) noexcept nogil:
    return edge.static_distance * (1.0 + edge.dynamic_congestion_weight)

cdef float _astar_internal(VenueGraph* graph, unsigned int start_id, unsigned int goal_id) noexcept nogil:
    if start_id == goal_id: return 0.0
    
    cdef unsigned int i = 0
    cdef float* g_scores = <float*>malloc(graph.node_count * sizeof(float))
    if not g_scores: return -1.0
    
    for i in range(graph.node_count): 
        g_scores[i] = 3.402823466e+38 # FLT_MAX
    
    g_scores[start_id] = 0.0
    
    cdef MinPriorityQueue pq
    cdef PQElement start_elem
    start_elem.node_id = start_id
    start_elem.f_score = 0.0
    pq.push(start_elem)
    
    cdef PQElement current
    cdef Node* n_neighbor = NULL
    cdef float lat_goal = graph.nodes[goal_id].lat
    cdef float lon_goal = graph.nodes[goal_id].lon
    cdef Node* current_node = NULL
    cdef Edge* edge = NULL
    cdef float tentative_g_score = 0.0
    cdef float h_score = 0.0
    cdef unsigned int neighbor_id = 0
    
    while not pq.empty():
        current = pq.top()
        pq.pop()
        
        if current.node_id == goal_id:
            h_score = g_scores[goal_id]
            free(g_scores)
            return h_score
            
        if current.f_score > g_scores[current.node_id]:
            continue
            
        current_node = &graph.nodes[current.node_id]
        
        for i in range(current_node.edge_start_idx, current_node.edge_start_idx + current_node.edge_count):
            edge = &graph.edges[i]
            neighbor_id = edge.target_id
            tentative_g_score = g_scores[current.node_id] + get_edge_weight(edge)
            
            if tentative_g_score < g_scores[neighbor_id]:
                g_scores[neighbor_id] = tentative_g_score
                n_neighbor = &graph.nodes[neighbor_id]
                h_score = haversine_heuristic(
                    n_neighbor.lat, n_neighbor.lon,
                    lat_goal, lon_goal
                )
                start_elem.node_id = neighbor_id
                start_elem.f_score = tentative_g_score + h_score
                pq.push(start_elem)
                
    free(g_scores)
    return -1.0 # No path

from libcpp.vector cimport vector
from libcpp.queue cimport queue
from libcpp.utility cimport pair

ctypedef pair[unsigned int, unsigned int] NodeDepth

cpdef get_subgraph(unsigned int start_id, unsigned int depth):
    """
    Bare-metal BFS traversal from start_id up to 'depth' edges away.
    Returns a list of node IDs. Executed entirely within nogil block.
    """
    global _global_graph
    if _global_graph.node_count == 0 or start_id >= _global_graph.node_count:
        return []

    cdef vector[unsigned int] result
    cdef vector[char] visited
    visited.resize(_global_graph.node_count, 0)
    
    cdef queue[NodeDepth] q
    cdef NodeDepth entry
    cdef NodeDepth current
    cdef unsigned int curr_id, curr_depth, i, neighbor_id
    cdef Node* node
    cdef Edge* edge
    
    with nogil:
        visited[start_id] = 1
        entry.first = start_id
        entry.second = 0
        q.push(entry)
        
        while not q.empty():
            current = q.front()
            q.pop()
            
            curr_id = current.first
            curr_depth = current.second
            result.push_back(curr_id)
            
            if curr_depth < depth:
                node = &_global_graph.nodes[curr_id]
                for i in range(node.edge_start_idx, node.edge_start_idx + node.edge_count):
                    edge = &_global_graph.edges[i]
                    neighbor_id = edge.target_id
                    if not visited[neighbor_id]:
                        visited[neighbor_id] = 1
                        entry.first = neighbor_id
                        entry.second = curr_depth + 1
                        q.push(entry)
                        
    return result
