import api from './api'

export interface Corporation {
  id: number
  corporation_id: number
  corporation_name: string
  ticker: string | null
  ceo_id: number | null
  ceo_name: string | null
  alliance_id: number | null
  alliance_name: string | null
  member_count: number | null
  tax_rate: number | null
  description: string | null
  url: string | null
  faction_id: number | null
  home_station_id: number | null
  last_synced_at: string | null
}

export interface CorporationMember {
  id: number
  character_id: number
  character_name: string
  start_date: string | null
  roles: string[] | null
  grantable_roles: string[] | null
  roles_at_hq: string[] | null
  roles_at_base: string[] | null
  roles_at_other: string[] | null
  last_synced_at: string | null
}

export interface CorporationAsset {
  id: number
  type_id: number
  type_name: string | null
  quantity: number
  location_id: number | null
  location_type: string | null
  location_name: string | null
  is_singleton: boolean
  item_id: number | null
  flag: string | null
  last_synced_at: string | null
}

export interface CorporationStructure {
  id: number
  structure_id: number
  structure_type_id: number | null
  structure_name: string | null
  system_id: number | null
  system_name: string | null
  fuel_expires: string | null
  state: string | null
  state_timer_start: string | null
  state_timer_end: string | null
  unanchors_at: string | null
  reinforce_hour: number | null
  reinforce_weekday: number | null
  services: any[] | null
  last_synced_at: string | null
}

export interface ListResponse<T> {
  items: T[]
  total: number
  skip: number
  limit: number
}

export const corporationsService = {
  /**
   * Get corporation by ID
   */
  get: async (corporationId: number, forceSync: boolean = false): Promise<Corporation> => {
    const params = forceSync ? '?force_sync=true' : ''
    const response = await api.get(`/corporations/${corporationId}${params}`)
    return response.data
  },

  /**
   * Get corporation members
   */
  getMembers: async (
    corporationId: number,
    skip: number = 0,
    limit: number = 100
  ): Promise<ListResponse<CorporationMember>> => {
    const response = await api.get(
      `/corporations/${corporationId}/members?skip=${skip}&limit=${limit}`
    )
    return response.data
  },

  /**
   * Get corporation assets
   */
  getAssets: async (
    corporationId: number,
    locationId?: number,
    skip: number = 0,
    limit: number = 1000
  ): Promise<ListResponse<CorporationAsset>> => {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
    })
    if (locationId) params.append('location_id', locationId.toString())
    
    const response = await api.get(`/corporations/${corporationId}/assets?${params.toString()}`)
    return response.data
  },

  /**
   * Get corporation structures
   */
  getStructures: async (
    corporationId: number,
    systemId?: number,
    skip: number = 0,
    limit: number = 100
  ): Promise<ListResponse<CorporationStructure>> => {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
    })
    if (systemId) params.append('system_id', systemId.toString())
    
    const response = await api.get(`/corporations/${corporationId}/structures?${params.toString()}`)
    return response.data
  },

  /**
   * Trigger corporation data sync
   */
  sync: async (corporationId: number, characterId: number): Promise<{ message: string }> => {
    const response = await api.post(
      `/corporations/${corporationId}/sync?character_id=${characterId}`
    )
    return response.data
  },
}

