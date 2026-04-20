import { create } from 'zustand';

interface ZoneState {
  id: number;
  weight: number;
  occupancy?: number;
  capacity?: number;
  name?: string;
}

interface AIResponse {
  answer?: string;
  recommendation?: string;
  severity?: 'INFO' | 'WARNING' | 'CRITICAL';
  protocol?: Array<{ zone_id: string; action: string }>;
}

interface VenueStore {
  zones: Record<number, ZoneState>;
  nodes: any[];
  edges: any[];
  configs: Record<string, any>;
  token: string | null;
  staffAlerts: AIResponse[];
  attendeeMessages: AIResponse[];
  
  // State management
  setVenueData: (data: { nodes: any[], edges: any[], configs: Record<string, any> }) => void;
  updateZone: (id: number, weight: number) => void;
  setToken: (token: string | null) => void;
  addStaffAlert: (alert: AIResponse) => void;
  addAttendeeMessage: (msg: AIResponse) => void;
}

export const useVenueStore = create<VenueStore>((set) => ({
  zones: {},
  nodes: [],
  edges: [],
  configs: {},
  token: localStorage.getItem('ef_token'),
  staffAlerts: [],
  attendeeMessages: [],

  setVenueData: (data) => set({ 
    nodes: data.nodes, 
    edges: data.edges, 
    configs: data.configs 
  }),

  updateZone: (id, weight) => set((state) => ({
    zones: {
      ...state.zones,
      [id]: { ...state.zones[id], id, weight }
    }
  })),

  setToken: (token) => {
    if (token) localStorage.setItem('ef_token', token);
    else localStorage.removeItem('ef_token');
    set({ token });
  },

  addStaffAlert: (alert) => set((state) => ({
    staffAlerts: [alert, ...state.staffAlerts].slice(0, 10)
  })),

  addAttendeeMessage: (msg) => set((state) => ({
    attendeeMessages: [...state.attendeeMessages, msg]
  })),
}));
