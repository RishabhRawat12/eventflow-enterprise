#ifndef PQ_H
#define PQ_H

#include <queue>
#include <vector>

struct PQElement {
    unsigned int node_id;
    float f_score;

    // Overload the less-than operator to act as a min-heap
    bool operator<(const PQElement& other) const {
        return f_score > other.f_score; 
    }
};

typedef std::priority_queue<PQElement> MinPriorityQueue;

#endif
