import api from './api'

export interface MarketOrder {
  id: number
  order_id: number
  type_id: number
  type_name: string | null
  is_buy_order: boolean
  location_id: number
  location_type: string | null
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
  issued: string
  expires: string | null
  is_active: boolean
  range_type: string | null
  range_value: number | null
}

export interface PriceHistory {
  id: number
  type_id: number
  type_name: string | null
  region_id: number
  region_name: string | null
  average_price: number | null
  highest_price: number | null
  lowest_price: number | null
  order_count: number | null
  volume: number | null
  date: string
}

export interface MarketPrices {
  best_buy: MarketOrder | null
  best_sell: MarketOrder | null
  average_buy: number | null
  average_sell: number | null
}

export interface ListResponse<T> {
  items: T[]
  total: number
  skip: number
  limit: number
}

export interface MarketOrderFilters {
  region_id?: number
  system_id?: number
  type_id?: number
  is_buy_order?: boolean
  location_id?: number
  min_price?: number
  max_price?: number
  skip?: number
  limit?: number
}

export const marketService = {
  /**
   * Get market orders with filters
   */
  getOrders: async (filters: MarketOrderFilters = {}): Promise<ListResponse<MarketOrder>> => {
    const params = new URLSearchParams()
    if (filters.region_id) params.append('region_id', filters.region_id.toString())
    if (filters.system_id) params.append('system_id', filters.system_id.toString())
    if (filters.type_id) params.append('type_id', filters.type_id.toString())
    if (filters.is_buy_order !== undefined) params.append('is_buy_order', filters.is_buy_order.toString())
    if (filters.location_id) params.append('location_id', filters.location_id.toString())
    if (filters.min_price !== undefined) params.append('min_price', filters.min_price.toString())
    if (filters.max_price !== undefined) params.append('max_price', filters.max_price.toString())
    if (filters.skip !== undefined) params.append('skip', filters.skip.toString())
    if (filters.limit !== undefined) params.append('limit', filters.limit.toString())
    
    const response = await api.get(`/market/orders?${params.toString()}`)
    return response.data
  },

  /**
   * Get current market prices for an item type
   */
  getPrices: async (
    typeId: number,
    regionId?: number,
    systemId?: number
  ): Promise<MarketPrices> => {
    const params = new URLSearchParams()
    if (regionId) params.append('region_id', regionId.toString())
    if (systemId) params.append('system_id', systemId.toString())
    
    const response = await api.get(`/market/prices/${typeId}?${params.toString()}`)
    return response.data
  },

  /**
   * Get price history for an item type
   */
  getPriceHistory: async (
    typeId: number,
    regionId: number,
    days: number = 30
  ): Promise<PriceHistory[]> => {
    const response = await api.get(
      `/market/prices/${typeId}/history?region_id=${regionId}&days=${days}`
    )
    return response.data
  },

  /**
   * Trigger market sync for a region
   */
  sync: async (regionId: number, systemId?: number): Promise<{ message: string }> => {
    const params = systemId ? `?system_id=${systemId}` : ''
    const response = await api.post(`/market/sync/${regionId}${params}`)
    return response.data
  },
}

