/**
 * Fittings API Service
 */
import api from './api';

export interface Fitting {
  id: number;
  fitting_id: number;
  name: string;
  description: string | null;
  ship_type_id: number;
  items: Array<{
    type_id: number;
    flag: string;
    quantity: number;
  }>;
}

export const fittingsService = {
  /**
   * List fittings
   */
  listFittings: async (params?: {
    character_id?: number;
    ship_type_id?: number;
    limit?: number;
    offset?: number;
  }) => {
    const response = await api.get<Fitting[]>('/fittings/', { params });
    return response.data;
  },

  /**
   * Get a specific fitting
   */
  getFitting: async (fittingId: number) => {
    const response = await api.get<Fitting>(`/fittings/${fittingId}`);
    return response.data;
  },

  /**
   * Delete a fitting
   */
  deleteFitting: async (fittingId: number) => {
    const response = await api.delete(`/fittings/${fittingId}`);
    return response.data;
  },

  /**
   * Trigger fitting sync
   */
  triggerSync: async (characterId: number) => {
    const response = await api.post(`/fittings/sync/${characterId}`);
    return response.data;
  },
};
