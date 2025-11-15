import axios from 'axios'

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000'

const getAuthHeader = () => {
  const token = localStorage.getItem('access_token')
  return token ? { headers: { Authorization: `Bearer ${token}` } } : {}
}

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
    const response = await axios.get(`${API_BASE_URL}/incursions/`, {
      params: { active_only: activeOnly },
      ...getAuthHeader(),
    })
    return response.data
  },

  async getIncursion(constellationId: number): Promise<Incursion> {
    const response = await axios.get(
      `${API_BASE_URL}/incursions/${constellationId}`,
      {
        ...getAuthHeader(),
      }
    )
    return response.data
  },

  async getIncursionStatistics(
    constellationId: number
  ): Promise<IncursionStatistics> {
    const response = await axios.get(
      `${API_BASE_URL}/incursions/${constellationId}/statistics`,
      {
        ...getAuthHeader(),
      }
    )
    return response.data
  },

  async getIncursionSummary(): Promise<IncursionSummary> {
    const response = await axios.get(`${API_BASE_URL}/incursions/summary`, {
      ...getAuthHeader(),
    })
    return response.data
  },

  async syncIncursions(): Promise<void> {
    await axios.post(
      `${API_BASE_URL}/incursions/sync`,
      {},
      {
        ...getAuthHeader(),
      }
    )
  },

  async recordParticipation(
    characterId: number,
    constellationId: number,
    siteType: string,
    iskEarned: number
  ): Promise<void> {
    await axios.post(
      `${API_BASE_URL}/incursions/participation`,
      {
        character_id: characterId,
        constellation_id: constellationId,
        site_type: siteType,
        isk_earned: iskEarned,
      },
      {
        ...getAuthHeader(),
      }
    )
  },
}
