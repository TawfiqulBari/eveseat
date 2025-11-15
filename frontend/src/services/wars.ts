import axios from 'axios'

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000'

const getAuthHeader = () => {
  const token = localStorage.getItem('access_token')
  return token ? { headers: { Authorization: `Bearer ${token}` } } : {}
}

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
    const response = await axios.get(`${API_BASE_URL}/wars/`, {
      params: { active_only: activeOnly },
      ...getAuthHeader(),
    })
    return response.data
  },

  async getWar(warId: number): Promise<War> {
    const response = await axios.get(`${API_BASE_URL}/wars/${warId}`, {
      ...getAuthHeader(),
    })
    return response.data
  },

  async getWarKillmails(warId: number): Promise<WarKillmail[]> {
    const response = await axios.get(`${API_BASE_URL}/wars/${warId}/killmails`, {
      ...getAuthHeader(),
    })
    return response.data
  },

  async getWarStatistics(): Promise<WarStatistics> {
    const response = await axios.get(`${API_BASE_URL}/wars/statistics`, {
      ...getAuthHeader(),
    })
    return response.data
  },

  async syncWars(): Promise<void> {
    await axios.post(
      `${API_BASE_URL}/wars/sync`,
      {},
      {
        ...getAuthHeader(),
      }
    )
  },

  async syncWarKillmails(warId: number): Promise<void> {
    await axios.post(
      `${API_BASE_URL}/wars/${warId}/killmails/sync`,
      {},
      {
        ...getAuthHeader(),
      }
    )
  },
}
