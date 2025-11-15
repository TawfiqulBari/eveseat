import api from './api'

export interface Incursion {
  id: number
  constellation_id: number
  state: string
  staging_solar_system_id: number | null
  influence: number
  has_boss: boolean
  faction_id: number
  type: string
  is_active: boolean
  synced_at: string | null
  created_at: string
}

export interface IncursionStatistics {
  id: number
  incursion_id: number
  total_sites_completed: number
  total_isk_earned: number
  unique_participants: number
  average_isk_per_site: number
  synced_at: string | null
}

export interface IncursionParticipation {
  id: number
  incursion_id: number
  character_id: number
  site_type: string
  isk_earned: number
  completed_at: string
}

export interface IncursionSummary {
  total_active: number
  total_established: number
  total_withdrawing: number
  highest_influence: number
  incursions_with_boss: number
}

export const incursionsService = {
  async listIncursions(activeOnly: boolean = true): Promise<Incursion[]> {
    const response = await api.get('/incursions/', {
      params: { active_only: activeOnly },
    })
    return response.data
  },

  async getIncursion(constellationId: number): Promise<Incursion> {
    const response = await api.get(`/incursions/${constellationId}`)
    return response.data
  },

  async getIncursionStatistics(
    constellationId: number
  ): Promise<IncursionStatistics> {
    const response = await api.get(`/incursions/${constellationId}/statistics`)
    return response.data
  },

  async getIncursionSummary(): Promise<IncursionSummary> {
    const response = await api.get('/incursions/summary')
    return response.data
  },

  async syncIncursions(): Promise<void> {
    await api.post('/incursions/sync')
  },

  async recordParticipation(
    characterId: number,
    constellationId: number,
    siteType: string,
    iskEarned: number
  ): Promise<void> {
    await api.post('/incursions/participation', {
      character_id: characterId,
      constellation_id: constellationId,
      site_type: siteType,
      isk_earned: iskEarned,
    })
  },
}
