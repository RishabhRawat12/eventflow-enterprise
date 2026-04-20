import React from 'react';
import { useVenueStore } from '../store/useStore';

const NODES = [
  { id: 0, name: "NorthGate", lat: 34.0520, lon: -118.2430 },
  { id: 1, name: "SouthGate", lat: 34.0510, lon: -118.2440 },
  { id: 2, name: "MainArena", lat: 34.0515, lon: -118.2435 },
  { id: 3, name: "VIPSection", lat: 34.0525, lon: -118.2445 },
];

const EDGES = [
  { from: 0, to: 2 },
  { from: 1, to: 2 },
  { from: 2, to: 3 },
  { from: 3, to: 2 },
  { from: 0, to: 3 },
];

// Map projection helper
const project = (lat: number, lon: number) => {
  const x = (lon + 118.245) * 60000; // Scaled for 600px
  const y = (34.053 - lat) * 60000;
  return { x, y };
};

export const Map: React.FC = () => {
  const zones = useVenueStore((state) => state.zones);

  const getWeightColor = (weight: number) => {
    if (!weight || weight < 1) return 'var(--status-clear)';
    if (weight < 3) return 'var(--status-moderate)';
    if (weight < 7) return 'var(--status-crowded)';
    return 'var(--status-critical)';
  };

  return (
    <div className="map-view" role="application" aria-label="Venue Navigation Map">
      <svg viewBox="0 0 600 600" className="map-canvas">
        <defs>
          <marker id="arrow" markerWidth="10" markerHeight="10" refX="5" refY="5" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L0,10 L10,5 z" fill="var(--text-secondary)" />
          </marker>
        </defs>

        {/* Edges */}
        {EDGES.map((edge, i) => {
          const from = project(NODES[edge.from].lat, NODES[edge.from].lon);
          const to = project(NODES[edge.to].lat, NODES[edge.to].lon);
          return (
            <line
              key={i}
              x1={from.x} y1={from.y}
              x2={to.x} y2={to.y}
              stroke="var(--text-secondary)"
              strokeWidth="2"
              markerEnd="url(#arrow)"
              opacity="0.3"
            />
          );
        })}

        {/* Nodes */}
        {NODES.map((node) => {
          const { x, y } = project(node.lat, node.lon);
          const weight = zones[node.id]?.weight || 0;
          return (
            <g key={node.id}>
              <circle
                cx={x} cy={y} r="15"
                fill={getWeightColor(weight)}
                stroke="white"
                strokeWidth="2"
                tabIndex={0}
                role="button"
                aria-label={`${node.name}, Congestion weight: ${weight.toFixed(1)}`}
              />
              <text
                x={x} y={y + 30}
                textAnchor="middle"
                fill="var(--text-primary)"
                fontSize="12"
                fontWeight="bold"
              >
                {node.name}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
};
