import api from './api'

export interface Killmail {
  id: number
  killmail_id: number
  time: string
  system_id: number | null
  system_name: string | null
  victim_character_id: number | null
  victim_character_name: string | null
  victim_corporation_id: number | null
  victim_corporation_name: string | null
  victim_alliance_id: number | null
  victim_alliance_name: string | null
  victim_ship_type_id: number | null
  victim_ship_type_name: string | null
  value: number | null
  attackers_count: number | null
  zkill_url: string | null
}

export interface KillmailDetail extends Killmail {
  killmail_data: Record<string, any>
}

export interface KillmailListResponse {
  items: Killmail[]
  total: number
  skip: number
  limit: number
}

export interface KillmailFilters {
  skip?: number
  limit?: number
  character_id?: number
  corporation_id?: number
  alliance_id?: number
  system_id?: number
  ship_type_id?: number
  min_value?: number
  max_value?: number
  start_date?: string
  end_date?: string
}

export interface KillmailStats {
  period_days: number
  start_date: string
  end_date: string
  total_kills: number
  total_value: number
  average_value: number
  top_systems: Array<{ system_id: number; count: number }>
  top_ship_types: Array<{ ship_type_id: number; count: number }>
}

export const killmailsService = {
  /**
   * List killmails with filters
   */
  list: async (filters: KillmailFilters = {}): Promise<KillmailListResponse> => {
    const params = new URLSearchParams()
    if (filters.skip !== undefined) params.append('skip', filters.skip.toString())
    if (filters.limit !== undefined) params.append('limit', filters.limit.toString())
    if (filters.character_id) params.append('character_id', filters.character_id.toString())
    if (filters.corporation_id) params.append('corporation_id', filters.corporation_id.toString())
    if (filters.alliance_id) params.append('alliance_id', filters.alliance_id.toString())
    if (filters.system_id) params.append('system_id', filters.system_id.toString())
    if (filters.ship_type_id) params.append('ship_type_id', filters.ship_type_id.toString())
    if (filters.min_value !== undefined) params.append('min_value', filters.min_value.toString())
    if (filters.max_value !== undefined) params.append('max_value', filters.max_value.toString())
    if (filters.start_date) params.append('start_date', filters.start_date)
    if (filters.end_date) params.append('end_date', filters.end_date)
    
    const response = await api.get(`/killmails?${params.toString()}`)
    return response.data
  },

  /**
   * Get killmail details by ID
   */
  get: async (killmailId: number): Promise<KillmailDetail> => {
    const response = await api.get(`/killmails/${killmailId}`)
    return response.data
  },

  /**
   * Get killmail statistics
   */
  getStats: async (params?: {
    character_id?: number
    corporation_id?: number
    alliance_id?: number
    days?: number
  }): Promise<KillmailStats> => {
    const queryParams = new URLSearchParams()
    if (params?.character_id) queryParams.append('character_id', params.character_id.toString())
    if (params?.corporation_id) queryParams.append('corporation_id', params.corporation_id.toString())
    if (params?.alliance_id) queryParams.append('alliance_id', params.alliance_id.toString())
    if (params?.days) queryParams.append('days', params.days.toString())
    
    const response = await api.get(`/killmails/stats?${queryParams.toString()}`)
    return response.data
  },
}
