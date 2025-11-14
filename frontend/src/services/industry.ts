/**
 * Industry API Service
 */
import api from './api';

export interface IndustryJob {
  id: number;
  job_id: number;
  installer_id: number;
  facility_id: number;
  location_id: number;
  activity_id: number;
  blueprint_type_id: number;
  product_type_id: number | null;
  runs: number;
  cost: number | null;
  status: string;
  start_date: string;
  end_date: string;
  completed_date: string | null;
  successful_runs: number | null;
}

export interface IndustryFacility {
  id: number;
  facility_id: number;
  owner_id: number;
  solar_system_id: number;
  type_id: number | null;
  name: string | null;
  bonuses: Record<string, any> | null;
  tax: number | null;
}

export interface IndustryStatistics {
  total_jobs: number;
  active_jobs: number;
  completed_jobs: number;
  total_runs: number;
  total_cost: number;
  by_activity: Record<string, {
    jobs: number;
    runs: number;
    cost: number;
  }>;
}

export const industryService = {
  /**
   * List industry jobs
   */
  listJobs: async (params?: {
    character_id?: number;
    activity_id?: number;
    status?: string;
    limit?: number;
    offset?: number;
  }) => {
    const response = await api.get<IndustryJob[]>('/industry/jobs/', { params });
    return response.data;
  },

  /**
   * Get a specific industry job
   */
  getJob: async (jobId: number) => {
    const response = await api.get<IndustryJob>(`/industry/jobs/${jobId}`);
    return response.data;
  },

  /**
   * List industry facilities
   */
  listFacilities: async (params?: {
    character_id?: number;
    solar_system_id?: number;
    limit?: number;
    offset?: number;
  }) => {
    const response = await api.get<IndustryFacility[]>('/industry/facilities/', { params });
    return response.data;
  },

  /**
   * Get industry statistics
   */
  getStatistics: async (characterId: number, days: number = 30) => {
    const response = await api.get<IndustryStatistics>(`/industry/statistics/${characterId}`, {
      params: { days },
    });
    return response.data;
  },

  /**
   * Trigger industry sync
   */
  triggerSync: async (characterId: number) => {
    const response = await api.post(`/industry/sync/${characterId}`);
    return response.data;
  },
};
