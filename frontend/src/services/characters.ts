import api from './api'

export interface Character {
  id: number
  character_id: number
  character_name: string
  corporation_id: number | null
  corporation_name: string | null
  alliance_id: number | null
  alliance_name: string | null
  security_status: number | null
  birthday: string | null
  gender: string | null
  race_id: number | null
  bloodline_id: number | null
  ancestry_id: number | null
  last_synced_at: string | null
}

export const charactersService = {
  /**
   * List all characters
   */
  list: async (params?: {
    user_id?: number
    corporation_id?: number
    alliance_id?: number
  }): Promise<Character[]> => {
    const queryParams = new URLSearchParams()
    if (params?.user_id) queryParams.append('user_id', params.user_id.toString())
    if (params?.corporation_id) queryParams.append('corporation_id', params.corporation_id.toString())
    if (params?.alliance_id) queryParams.append('alliance_id', params.alliance_id.toString())
    
    const response = await api.get(`/characters?${queryParams.toString()}`)
    return response.data
  },

  /**
   * Get character by ID
   */
  get: async (characterId: number): Promise<Character> => {
    const response = await api.get(`/characters/${characterId}`)
    return response.data
  },
}

