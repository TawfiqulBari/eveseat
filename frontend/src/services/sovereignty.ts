/**
 * Sovereignty API service
 */
import api from './api'

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

export const sovereigntyService = {
  async listSystems(params: ListSystemsParams): Promise<SystemSovereignty[]> {
    const response = await api.get('/sov/systems', { params })
    return response.data
  },

  async getSystem(systemId: number): Promise<SystemSovereignty> {
    const response = await api.get(`/sov/systems/${systemId}`)
    return response.data
  },

  async listStructures(params: ListStructuresParams): Promise<SovereigntyStructure[]> {
    const response = await api.get('/sov/structures', { params })
    return response.data
  },

  async listCampaigns(params: ListCampaignsParams): Promise<SovereigntyCampaign[]> {
    const response = await api.get('/sov/campaigns', { params })
    return response.data
  },

  async getStatistics(): Promise<SovereigntyStatistics> {
    const response = await api.get('/sov/statistics')
    return response.data
  },

  async triggerSync(): Promise<void> {
    await api.post('/sov/sync')
  },
}
