/**
 * Blueprints API Service
 */
import api from './api';

export interface Blueprint {
  id: number;
  item_id: number;
  type_id: number;
  location_id: number;
  location_flag: string;
  quantity: number;
  time_efficiency: number;
  material_efficiency: number;
  runs: number;
}

export interface BlueprintStatistics {
  total_blueprints: number;
  bpos: number;
  bpcs: number;
  avg_me: number;
  avg_te: number;
  fully_researched: number;
}

export const blueprintsService = {
  /**
   * List blueprints
   */
  listBlueprints: async (params?: {
    character_id?: number;
    location_id?: number;
    is_original?: boolean;
    limit?: number;
    offset?: number;
  }) => {
    const response = await api.get<Blueprint[]>('/blueprints/', { params });
    return response.data;
  },

  /**
   * Get a specific blueprint
   */
  getBlueprint: async (blueprintId: number) => {
    const response = await api.get<Blueprint>(`/blueprints/${blueprintId}`);
    return response.data;
  },

  /**
   * Get blueprint statistics
   */
  getStatistics: async (characterId: number) => {
    const response = await api.get<BlueprintStatistics>(`/blueprints/statistics/${characterId}`);
    return response.data;
  },

  /**
   * Trigger blueprint sync
   */
  triggerSync: async (characterId: number) => {
    const response = await api.post(`/blueprints/sync/${characterId}`);
    return response.data;
  },
};
