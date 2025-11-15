/**
 * Sovereignty API service
 */
import axios from 'axios'

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000'

export interface SystemSovereignty {
  id: number
  system_id: number
  alliance_id: number | null
  corporation_id: number | null
  faction_id: number | null
  ihub_vulnerability_timer: number | null
  tcu_vulnerability_timer: number | null
  synced_at: string | null
}

export interface SovereigntyStructure {
  id: number
  structure_id: number
  system_id: number
  structure_type_id: number
  alliance_id: number
  vulnerable_start_time: string | null
  vulnerable_end_time: string | null
  vulnerability_occupancy_level: number | null
  synced_at: string | null
}

export interface SovereigntyCampaign {
  id: number
  campaign_id: number
  system_id: number
  constellation_id: number
  structure_id: number
  event_type: string
  defender_id: number | null
  defender_score: number
  attackers_score: number
  start_time: string
  synced_at: string | null
}

export interface SovereigntyStatistics {
  total_systems: number
  systems_by_alliance: { [key: string]: number }
  systems_by_faction: { [key: string]: number }
  vulnerable_structures: number
  active_campaigns: number
}

interface ListSystemsParams {
  alliance_id?: number
  corporation_id?: number
  faction_id?: number
  limit?: number
  offset?: number
}

interface ListStructuresParams {
  alliance_id?: number
  system_id?: number
  limit?: number
  offset?: number
}

interface ListCampaignsParams {
  system_id?: number
  defender_id?: number
  limit?: number
  offset?: number
}

const getAuthHeader = () => {
  const token = localStorage.getItem('access_token')
  return {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  }
}

export const sovereigntyService = {
  async listSystems(params: ListSystemsParams): Promise<SystemSovereignty[]> {
    const response = await axios.get(`${API_BASE_URL}/sov/systems`, {
      params,
      ...getAuthHeader(),
    })
    return response.data
  },

  async getSystem(systemId: number): Promise<SystemSovereignty> {
    const response = await axios.get(`${API_BASE_URL}/sov/systems/${systemId}`, getAuthHeader())
    return response.data
  },

  async listStructures(params: ListStructuresParams): Promise<SovereigntyStructure[]> {
    const response = await axios.get(`${API_BASE_URL}/sov/structures`, {
      params,
      ...getAuthHeader(),
    })
    return response.data
  },

  async listCampaigns(params: ListCampaignsParams): Promise<SovereigntyCampaign[]> {
    const response = await axios.get(`${API_BASE_URL}/sov/campaigns`, {
      params,
      ...getAuthHeader(),
    })
    return response.data
  },

  async getStatistics(): Promise<SovereigntyStatistics> {
    const response = await axios.get(`${API_BASE_URL}/sov/statistics`, getAuthHeader())
    return response.data
  },

  async triggerSync(): Promise<void> {
    await axios.post(`${API_BASE_URL}/sov/sync`, {}, getAuthHeader())
  },
}
