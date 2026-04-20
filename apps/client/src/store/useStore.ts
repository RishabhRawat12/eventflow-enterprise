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
  staffAlerts: AIResponse[];
  attendeeMessages: AIResponse[];
  
  // High-frequency granular update
  updateZone: (id: number, weight: number) => void;
  
  // AI State management
  addStaffAlert: (alert: AIResponse) => void;
  addAttendeeMessage: (msg: AIResponse) => void;
}

export const useVenueStore = create<VenueStore>((set) => ({
  zones: {},
  staffAlerts: [],
  attendeeMessages: [],

  updateZone: (id, weight) => set((state) => ({
    zones: {
      ...state.zones,
      [id]: { ...state.zones[id], id, weight }
    }
  })),

  addStaffAlert: (alert) => set((state) => ({
    staffAlerts: [alert, ...state.staffAlerts].slice(0, 10) // Keep last 10
  })),

  addAttendeeMessage: (msg) => set((state) => ({
    attendeeMessages: [...state.attendeeMessages, msg]
  })),
}));
