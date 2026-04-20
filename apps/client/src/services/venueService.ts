import { useVenueStore } from '../store/useStore';

export const fetchVenueData = async () => {
  const token = localStorage.getItem('ef_token');
  if (!token) throw new Error('No authentication token');

  const response = await fetch('/api/v1/venue/', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });

  if (!response.ok) {
    if (response.status === 401) {
      useVenueStore.getState().setToken(null);
    }
    throw new Error('Failed to fetch venue geometry');
  }

  const data = await response.json();
  useVenueStore.getState().setVenueData(data);
  return data;
};
