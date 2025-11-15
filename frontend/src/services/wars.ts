import api from './api'

export interface War {
  id: number
  war_id: number
  declared: string | null
  started: string | null
  finished: string | null
  is_mutual: boolean
  is_open_for_allies: boolean
  aggressor_alliance_id: number | null
  defender_alliance_id: number | null
  aggressor_ships_killed: number
  defender_ships_killed: number
  aggressor_isk_destroyed: number
  defender_isk_destroyed: number
  is_active: boolean
  synced_at: string | null
  created_at: string
}

export interface WarAlly {
  id: number
  war_id: number
  alliance_id: number
  alliance_name: string
  joined_date: string | null
}

export interface WarKillmail {
  id: number
  war_id: number
  killmail_id: number
  killmail_hash: string
  recorded_at: string
}

export interface WarStatistics {
  total_wars: number
  active_wars: number
  total_kills: number
  total_isk_destroyed: number
  most_active_war: {
    war_id: number
    total_kills: number
  } | null
}

export const warsService = {
  async listWars(activeOnly: boolean = true): Promise<War[]> {
    const response = await api.get('/wars/', {
      params: { active_only: activeOnly },
    })
    return response.data
  },

  async getWar(warId: number): Promise<War> {
    const response = await api.get(`/wars/${warId}`)
    return response.data
  },

  async getWarKillmails(warId: number): Promise<WarKillmail[]> {
    const response = await api.get(`/wars/${warId}/killmails`)
    return response.data
  },

  async getWarStatistics(): Promise<WarStatistics> {
    const response = await api.get('/wars/statistics')
    return response.data
  },

  async syncWars(): Promise<void> {
    await api.post('/wars/sync')
  },

  async syncWarKillmails(warId: number): Promise<void> {
    await api.post(`/wars/${warId}/killmails/sync`)
  },
}
