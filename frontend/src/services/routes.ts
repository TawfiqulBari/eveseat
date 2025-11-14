import api from './api'

export interface RouteSystemInfo {
  system_id: number
  system_name: string
  security_status: number
  security_class: string | null
  region_id: number
  region_name: string | null
  constellation_id: number
  constellation_name: string | null
  x: number | null
  y: number | null
  z: number | null
}

export interface RouteRequest {
  start_system_id: number
  end_system_id: number
  waypoints?: number[]
  avoid_systems?: number[]
  avoid_regions?: number[]
  prefer_safer?: boolean
  security_penalty?: number
  max_jumps?: number
}

export interface RouteResponse {
  route: RouteSystemInfo[]
  total_jumps: number
  estimated_time_seconds: number
  average_security: number
  route_length: number
  segments?: any[]
  error?: string
}

export const routesService = {
  /**
   * Calculate route between systems
   */
  calculate: async (request: RouteRequest): Promise<RouteResponse> => {
    const response = await api.post('/routes/calculate', request)
    return response.data
  },
}

