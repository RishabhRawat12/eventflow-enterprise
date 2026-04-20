import { useEffect, useRef } from 'react';
import { useVenueStore } from '../store/useStore';

export const useWebSocket = (venueId: string) => {
  const updateZone = useVenueStore((state) => state.updateZone);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Determine the WS URL (using the same host as the current location)
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/venue/${venueId}`;
    
    console.log(`[WS] Connecting to ${wsUrl}...`);
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onmessage = (event) => {
      try {
        // Parse minified JSON: {"z": 14, "w": 5.2}
        const data = JSON.parse(event.data);
        if (data.z !== undefined && data.w !== undefined) {
          // Direct store update (Optimized)
          updateZone(data.z, data.w);
        }
      } catch (err) {
        console.error('[WS_PARSE_ERROR]', err);
      }
    };

    socket.onopen = () => console.log('[WS] Connected.');
    socket.onclose = () => console.log('[WS] Disconnected.');
    socket.onerror = (err) => console.error('[WS_ERROR]', err);

    return () => {
      socket.close();
    };
  }, [venueId, updateZone]);

  return socketRef.current;
};
