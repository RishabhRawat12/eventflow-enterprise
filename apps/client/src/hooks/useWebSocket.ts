import { useEffect, useRef } from 'react';
import { useVenueStore } from '../store/useStore';
import { fetchVenueData } from '../services/venueService';

export const useWebSocket = (venueId: string) => {
  const { updateZone, token } = useVenueStore();
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!token) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/venue/${venueId}?token=${token}`;
    
    console.log(`[WS] Connecting to ${wsUrl}...`);
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Handle atomic system events
        if (data.type === 'RELOAD') {
          console.log('[WS] System RELOAD triggered. Fetching fresh geometry...');
          fetchVenueData().catch(console.error);
        } 
        // Handle granular telemetry
        else if (data.z !== undefined && data.w !== undefined) {
          updateZone(data.z, data.w);
        }
      } catch (err) {
        console.error('[WS_PARSE_ERROR]', err);
      }
    };

    socket.onopen = () => console.log('[WS] Secured Connection Active.');
    socket.onclose = (e) => {
      if (e.code === 4003) {
        console.error('[WS] Auth Failed: Unauthorized.');
      }
    };

    return () => socket.close();
  }, [venueId, updateZone, token]);

  return socketRef.current;
};
