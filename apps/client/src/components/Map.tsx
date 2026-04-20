import React, { useEffect, useMemo } from 'react';
import { useVenueStore } from '../store/useStore';
import { fetchVenueData } from '../services/venueService';

export const Map: React.FC = () => {
  const { nodes, edges, zones, configs, token } = useVenueStore();

  // Initial fetch on mount or token change
  useEffect(() => {
    if (token && nodes.length === 0) {
      fetchVenueData().catch(console.error);
    }
  }, [token]);

  // Dynamic projection helper based on current node extents
  const projection = useMemo(() => {
    if (nodes.length === 0) return { scale: 1, offsetX: 0, offsetY: 0 };
    
    const lats = nodes.map(n => n.lat);
    const lons = nodes.map(n => n.lon);
    
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLon = Math.min(...lons);
    const maxLon = Math.max(...lons);
    
    const latDiff = maxLat - minLat || 0.001;
    const lonDiff = maxLon - minLon || 0.001;
    
    // Scale to fit 500x500 with padding
    const scale = 400 / Math.max(latDiff, lonDiff);
    
    return {
      scale,
      minLat,
      minLon,
      offsetX: 50,
      offsetY: 50
    };
  }, [nodes]);

  const project = (lat: number, lon: number) => {
    const x = (lon - projection.minLon!) * projection.scale + projection.offsetX;
    const y = (projection.scale * (projection.minLat! + (projection.projectionLatDiff || 0) - lat)) + projection.offsetY;
    
    // Correcting the Y inversion for SVG (standard lat decreases as Y increases)
    const y_corrected = (projection.minLat! + (Math.max(...nodes.map(n => n.lat)) - projection.minLat!) - lat) * projection.scale + projection.offsetY;
    
    return { x, y: y_corrected };
  };

  const getWeightColor = (weight: number) => {
    if (!weight || weight < 1) return '#00FF9D'; // Neon Green
    if (weight < 3) return '#FFD700'; // Gold
    if (weight < 7) return '#FF8C00'; // Orange
    return '#FF3366'; // Neon Red
  };

  if (nodes.length === 0) {
    return (
      <div className="map-view loading" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '1rem' }}>
        <div className="pulse-loader" style={{ color: 'var(--accent-primary)', fontWeight: 'bold' }}>
          Sychronizing Spatial Index...
        </div>
        {!token && (
          <button 
            onClick={() => {
              // Trigger a mock auth for the demo or redirect to your Firebase login
              // For the hackathon bypass, we set the dev token
              const devToken = "dev-hackathon-2026";
              localStorage.setItem('ef_token', devToken);
              window.location.reload();
            }}
            style={{ 
              background: 'var(--accent-primary)', 
              color: 'black', 
              border: 'none', 
              padding: '0.5rem 1rem', 
              borderRadius: '6px',
              fontWeight: 'bold',
              cursor: 'pointer'
            }}
          >
            Authorize Secure Session
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="map-view" role="application" aria-label="Venue Navigation Map">
      <svg viewBox="0 0 600 600" className="map-canvas">
        <defs>
          <marker id="arrow" markerWidth="10" markerHeight="10" refX="5" refY="5" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L0,10 L10,5 z" fill="#8B949E" />
          </marker>
        </defs>

        {/* Edges */}
        {edges.map((edge, i) => {
          const fromNode = nodes.find(n => n.id === edge.from);
          const toNode = nodes.find(n => n.id === edge.to);
          if (!fromNode || !toNode) return null;

          const from = project(fromNode.lat, fromNode.lon);
          const to = project(toNode.lat, toNode.lon);

          return (
            <line
              key={`edge-${i}`}
              x1={from.x} y1={from.y}
              x2={to.x} y2={to.y}
              stroke="#8B949E"
              strokeWidth="1.5"
              markerEnd="url(#arrow)"
              opacity="0.2"
              className="map-edge"
            />
          );
        })}

        {/* Nodes */}
        {nodes.map((node) => {
          const { x, y } = project(node.lat, node.lon);
          const weight = zones[node.id]?.weight || 0;
          const color = getWeightColor(weight);
          
          return (
            <g key={`node-${node.id}`} className="map-node">
              <circle
                cx={x} cy={y} r="12"
                fill="transparent"
                stroke={color}
                strokeWidth="2"
                style={{ 
                  filter: `drop-shadow(0 0 4px ${color})`,
                  transition: 'stroke 0.3s ease, filter 0.3s ease' 
                }}
              />
              <text
                x={x} y={y + 25}
                textAnchor="middle"
                fill="#C9D1D9"
                fontSize="10"
                fontWeight="500"
                className="node-label"
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
