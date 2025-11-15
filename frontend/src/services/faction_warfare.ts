import axios from 'axios'

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000'

const getAuthHeader = () => {
  const token = localStorage.getItem('access_token')
  return token ? { headers: { Authorization: `Bearer ${token}` } } : {}
}

export interface FactionWarfareSystem {
  id: number
  solar_system_id: number
  solar_system_name?: string
  occupier_faction_id: number
  owner_faction_id: number
  contested: string
  victory_points: number
  victory_points_threshold: number
  synced_at: string | null
}

export interface FactionWarfareStatistics {
  id: number
  faction_id: number
  pilots: number
  systems_controlled: number
  kills_yesterday: number
  kills_last_week: number
  kills_total: number
  victory_points_yesterday: number
  victory_points_last_week: number
  victory_points_total: number
  synced_at: string | null
}

export interface CharacterFactionWarfare {
  id: number
  character_id: number
  faction_id: number | null
  enlisted: string | null
  current_rank: number
  highest_rank: number
  kills_yesterday: number
  kills_last_week: number
  kills_total: number
  victory_points_yesterday: number
  victory_points_last_week: number
  victory_points_total: number
  is_enrolled: boolean
  synced_at: string | null
}

export interface FactionWarfareLeaderboard {
  id: number
  character_id: number
  character_name?: string
  stat_type: string
  rank: number
  amount: number
  synced_at: string | null
}

export interface FactionWarfareSummary {
  total_systems: number
  contested_systems: number
  vulnerable_systems: number
  statistics_by_faction: {
    [factionId: number]: FactionWarfareStatistics
  }
}

export const factionWarfareService = {
  async listSystems(contestedOnly: boolean = false): Promise<FactionWarfareSystem[]> {
    const response = await axios.get(`${API_BASE_URL}/faction-warfare/systems`, {
      params: { contested_only: contestedOnly },
      ...getAuthHeader(),
    })
    return response.data
  },

  async getSystem(systemId: number): Promise<FactionWarfareSystem> {
    const response = await axios.get(
      `${API_BASE_URL}/faction-warfare/systems/${systemId}`,
      {
        ...getAuthHeader(),
      }
    )
    return response.data
  },

  async getStatistics(): Promise<FactionWarfareStatistics[]> {
    const response = await axios.get(`${API_BASE_URL}/faction-warfare/statistics`, {
      ...getAuthHeader(),
    })
    return response.data
  },

  async getFactionStatistics(factionId: number): Promise<FactionWarfareStatistics> {
    const response = await axios.get(
      `${API_BASE_URL}/faction-warfare/statistics/${factionId}`,
      {
        ...getAuthHeader(),
      }
    )
    return response.data
  },

  async getSummary(): Promise<FactionWarfareSummary> {
    const response = await axios.get(`${API_BASE_URL}/faction-warfare/summary`, {
      ...getAuthHeader(),
    })
    return response.data
  },

  async getCharacterStats(characterId: number): Promise<CharacterFactionWarfare> {
    const response = await axios.get(
      `${API_BASE_URL}/faction-warfare/character/${characterId}`,
      {
        ...getAuthHeader(),
      }
    )
    return response.data
  },

  async getLeaderboard(statType: string = 'kills_yesterday'): Promise<FactionWarfareLeaderboard[]> {
    const response = await axios.get(`${API_BASE_URL}/faction-warfare/leaderboard`, {
      params: { stat_type: statType },
      ...getAuthHeader(),
    })
    return response.data
  },

  async syncSystems(): Promise<void> {
    await axios.post(
      `${API_BASE_URL}/faction-warfare/sync`,
      {},
      {
        ...getAuthHeader(),
      }
    )
  },

  async syncCharacterStats(characterId: number): Promise<void> {
    await axios.post(
      `${API_BASE_URL}/faction-warfare/character/${characterId}/sync`,
      {},
      {
        ...getAuthHeader(),
      }
    )
  },
}
