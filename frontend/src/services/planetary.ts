/**
 * Planetary Interaction API Service
 */
import api from './api';

export interface Planet {
  id: number;
  planet_id: number;
  solar_system_id: number;
  planet_type: string;
  upgrade_level: number;
  num_pins: number;
  last_update: string | null;
}

export interface PlanetPin {
  id: number;
  pin_id: number;
  type_id: number;
  schematic_id: number | null;
  latitude: number | null;
  longitude: number | null;
  install_time: string | null;
  expiry_time: string | null;
  product_type_id: number | null;
  contents: Record<string, any> | null;
}

export interface PlanetDetail {
  planet: Planet;
  pins: PlanetPin[];
  extractions: Array<{
    pin_id: number;
    product_type_id: number;
    expiry_time: string;
    status: string;
  }>;
}

export interface PlanetStatistics {
  total_planets: number;
  active_extractors: number;
  expiring_soon: number;
  total_pins: number;
  by_planet_type: Record<string, number>;
}

export const planetaryService = {
  /**
   * List planets
   */
  listPlanets: async (params?: {
    character_id?: number;
    solar_system_id?: number;
    limit?: number;
    offset?: number;
  }) => {
    const response = await api.get<Planet[]>('/planetary/', { params });
    return response.data;
  },

  /**
   * Get planet details
   */
  getPlanet: async (planetId: number) => {
    const response = await api.get<PlanetDetail>(`/planetary/${planetId}`);
    return response.data;
  },

  /**
   * Get planetary statistics
   */
  getStatistics: async (characterId: number) => {
    const response = await api.get<PlanetStatistics>(`/planetary/statistics/${characterId}`);
    return response.data;
  },

  /**
   * Trigger planetary sync
   */
  triggerSync: async (characterId: number) => {
    const response = await api.post(`/planetary/sync/${characterId}`);
    return response.data;
  },
};
