/**
 * Clones API Service
 */
import api from './api';

export interface Clone {
  id: number;
  jump_clone_id: number;
  name: string | null;
  location_id: number;
  location_type: string | null;
  implants: number[];
}

export interface ActiveImplant {
  id: number;
  type_id: number;
  name: string | null;
  slot: number | null;
}

export interface CloneStatistics {
  total_jump_clones: number;
  clones_with_implants: number;
  active_implants: number;
  total_implant_value: number | null;
}

export const clonesService = {
  /**
   * List jump clones
   */
  listClones: async (params?: {
    character_id?: number;
    location_id?: number;
  }) => {
    const response = await api.get<Clone[]>('/clones/', { params });
    return response.data;
  },

  /**
   * Get active implants
   */
  getActiveImplants: async (characterId: number) => {
    const response = await api.get<ActiveImplant[]>('/clones/active-implants/', {
      params: { character_id: characterId },
    });
    return response.data;
  },

  /**
   * Get clone statistics
   */
  getStatistics: async (characterId: number) => {
    const response = await api.get<CloneStatistics>(`/clones/statistics/${characterId}`);
    return response.data;
  },

  /**
   * Trigger clone sync
   */
  triggerSync: async (characterId: number) => {
    const response = await api.post(`/clones/sync/${characterId}`);
    return response.data;
  },
};
