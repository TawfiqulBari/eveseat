import axios from 'axios'

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000'

const getAuthHeader = () => {
  const token = localStorage.getItem('access_token')
  return token ? { headers: { Authorization: `Bearer ${token}` } } : {}
}

export interface Alliance {
  id: number
  alliance_id: number
  alliance_name: string
  ticker: string
  executor_corporation_id: number | null
  date_founded: string | null
  member_count: number
  corporation_count: number
  synced_at: string | null
  created_at: string
}

export interface AllianceCorporation {
  id: number
  alliance_id: number
  corporation_id: number
  corporation_name: string
  joined_date: string | null
  synced_at: string | null
}

export interface AllianceContact {
  id: number
  alliance_id: number
  contact_id: number
  contact_type: string
  standing: number
  label_ids: number[]
  synced_at: string | null
}

export interface AllianceStatistics {
  total_members: number
  total_corporations: number
  active_wars: number
  total_kills_last_week: number
  total_losses_last_week: number
  top_killers: Array<{
    character_id: number
    character_name: string
    kills: number
  }>
}

export const alliancesService = {
  async listAlliances(): Promise<Alliance[]> {
    const response = await axios.get(`${API_BASE_URL}/alliances/`, {
      ...getAuthHeader(),
    })
    return response.data
  },

  async getAlliance(allianceId: number): Promise<Alliance> {
    const response = await axios.get(`${API_BASE_URL}/alliances/${allianceId}`, {
      ...getAuthHeader(),
    })
    return response.data
  },

  async getAllianceStatistics(allianceId: number): Promise<AllianceStatistics> {
    const response = await axios.get(
      `${API_BASE_URL}/alliances/${allianceId}/statistics`,
      {
        ...getAuthHeader(),
      }
    )
    return response.data
  },

  async syncAlliance(allianceId: number): Promise<void> {
    await axios.post(
      `${API_BASE_URL}/alliances/${allianceId}/sync`,
      {},
      {
        ...getAuthHeader(),
      }
    )
  },

  async listAllianceCorporations(allianceId: number): Promise<AllianceCorporation[]> {
    const response = await axios.get(
      `${API_BASE_URL}/alliances/${allianceId}/corporations`,
      {
        ...getAuthHeader(),
      }
    )
    return response.data
  },
}
