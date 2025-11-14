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

export interface CharacterAsset {
  item_id: number
  type_id: number
  type_name?: string
  type_icon_url?: string
  location_id: number
  location_name?: string
  location_type?: string
  system_id?: number
  system_name?: string
  region_name?: string
  quantity: number
  flag?: number
  singleton?: boolean
  items?: CharacterAsset[] // Nested items (containers)
}

export interface CharacterMarketOrder {
  id: number
  order_id: number
  character_id: number
  type_id: number
  type_name: string | null
  type_icon_url: string | null
  is_buy_order: boolean
  location_id: number
  location_name: string | null
  region_id: number | null
  region_name: string | null
  system_id: number | null
  system_name: string | null
  price: number
  volume_total: number
  volume_remain: number
  min_volume: number | null
  duration: number | null
  issued: string | null
  expires: string | null
  is_active: boolean
  range_type: string | null
  range_value: number | null
}

export interface CharacterDetails {
  character_id: number
  character_name: string
  corporation_id: number | null
  corporation_name: string | null
  alliance_id: number | null
  alliance_name: string | null
  security_status: string | null
  details: {
    character_info?: any
    corporation_info?: any
    alliance_info?: any
    contacts?: any[]
    standings?: any[]
    wallet_balance?: number
    location?: any
    ship?: any
    skill_queue?: any[]
    skills?: any
    [key: string]: any
  }
  synced_at: string | null
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

  /**
   * Get character assets
   */
  getAssets: async (characterId: number): Promise<{
    character_id: number
    assets: CharacterAsset[]
    count: number
    synced_at: string | null
  }> => {
    const response = await api.get(`/characters/${characterId}/assets`)
    return response.data
  },

  /**
   * Get character market orders
   */
  getMarketOrders: async (
    characterId: number,
    params?: {
      is_buy_order?: boolean
      is_active?: boolean
      skip?: number
      limit?: number
    }
  ): Promise<{
    items: CharacterMarketOrder[]
    total: number
    skip: number
    limit: number
  }> => {
    const queryParams = new URLSearchParams()
    if (params?.is_buy_order !== undefined) queryParams.append('is_buy_order', params.is_buy_order.toString())
    if (params?.is_active !== undefined) queryParams.append('is_active', params.is_active.toString())
    if (params?.skip) queryParams.append('skip', params.skip.toString())
    if (params?.limit) queryParams.append('limit', params.limit.toString())
    
    const response = await api.get(`/characters/${characterId}/market-orders?${queryParams.toString()}`)
    return response.data
  },

  /**
   * Get character details
   */
  getDetails: async (characterId: number): Promise<CharacterDetails> => {
    const response = await api.get(`/characters/${characterId}/details`)
    return response.data
  },

  /**
   * Trigger sync of character assets
   */
  syncAssets: async (characterId: number): Promise<{
    message: string
    task_id: string
    character_id: number
  }> => {
    const response = await api.post(`/characters/${characterId}/sync/assets`)
    return response.data
  },

  /**
   * Trigger sync of character market orders
   */
  syncMarketOrders: async (characterId: number): Promise<{
    message: string
    task_id: string
    character_id: number
  }> => {
    const response = await api.post(`/characters/${characterId}/sync/market-orders`)
    return response.data
  },

  /**
   * Trigger sync of character details
   */
  syncDetails: async (characterId: number): Promise<{
    message: string
    task_id: string
    character_id: number
  }> => {
    const response = await api.post(`/characters/${characterId}/sync/details`)
    return response.data
  },
}

