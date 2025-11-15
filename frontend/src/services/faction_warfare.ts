import api from './api'

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
    const response = await api.get('/faction-warfare/systems', {
      params: { contested_only: contestedOnly },
    })
    return response.data
  },

  async getSystem(systemId: number): Promise<FactionWarfareSystem> {
    const response = await api.get(`/faction-warfare/systems/${systemId}`)
    return response.data
  },

  async getStatistics(): Promise<FactionWarfareStatistics[]> {
    const response = await api.get('/faction-warfare/statistics')
    return response.data
  },

  async getFactionStatistics(factionId: number): Promise<FactionWarfareStatistics> {
    const response = await api.get(`/faction-warfare/statistics/${factionId}`)
    return response.data
  },

  async getSummary(): Promise<FactionWarfareSummary> {
    const response = await api.get('/faction-warfare/summary')
    return response.data
  },

  async getCharacterStats(characterId: number): Promise<CharacterFactionWarfare> {
    const response = await api.get(`/faction-warfare/character/${characterId}`)
    return response.data
  },

  async getLeaderboard(statType: string = 'kills_yesterday'): Promise<FactionWarfareLeaderboard[]> {
    const response = await api.get('/faction-warfare/leaderboard', {
      params: { stat_type: statType },
    })
    return response.data
  },

  async syncSystems(): Promise<void> {
    await api.post('/faction-warfare/sync')
  },

  async syncCharacterStats(characterId: number): Promise<void> {
    await api.post(`/faction-warfare/character/${characterId}/sync`)
  },
}
