import api from './api'

export interface System {
  id: number
  system_id: number
  system_name: string
  constellation_id: number
  constellation_name: string | null
  region_id: number
  region_name: string | null
  x: number | null
  y: number | null
  z: number | null
  security_status: number
  security_class: string | null
  system_type: string | null
}

export interface SystemActivity {
  system_id: number
  system_name: string | null
  kills_last_hour: number
  jumps_last_hour: number
  npc_kills_last_hour: number
  pod_kills_last_hour: number
  ship_kills_last_hour: number
  timestamp: string
}

export interface SystemFilters {
  region_id?: number
  constellation_id?: number
  min_security?: number
  max_security?: number
  system_type?: string
  skip?: number
  limit?: number
}

export interface ActivityFilters {
  system_id?: number
  region_id?: number
  hours?: number
  min_kills?: number
  skip?: number
  limit?: number
}

export const mapService = {
  /**
   * Get systems with filters
   */
  getSystems: async (filters: SystemFilters = {}): Promise<System[]> => {
    const params = new URLSearchParams()
    if (filters.region_id) params.append('region_id', filters.region_id.toString())
    if (filters.constellation_id) params.append('constellation_id', filters.constellation_id.toString())
    if (filters.min_security !== undefined) params.append('min_security', filters.min_security.toString())
    if (filters.max_security !== undefined) params.append('max_security', filters.max_security.toString())
    if (filters.system_type) params.append('system_type', filters.system_type)
    if (filters.skip !== undefined) params.append('skip', filters.skip.toString())
    if (filters.limit !== undefined) params.append('limit', filters.limit.toString())
    
    const response = await api.get(`/map/systems?${params.toString()}`)
    return response.data
  },

  /**
   * Get system by ID
   */
  getSystem: async (systemId: number): Promise<System> => {
    const response = await api.get(`/map/systems/${systemId}`)
    return response.data
  },

  /**
   * Get system activity
   */
  getActivity: async (filters: ActivityFilters = {}): Promise<SystemActivity[]> => {
    const params = new URLSearchParams()
    if (filters.system_id) params.append('system_id', filters.system_id.toString())
    if (filters.region_id) params.append('region_id', filters.region_id.toString())
    if (filters.hours !== undefined) params.append('hours', filters.hours.toString())
    if (filters.min_kills !== undefined) params.append('min_kills', filters.min_kills.toString())
    if (filters.skip !== undefined) params.append('skip', filters.skip.toString())
    if (filters.limit !== undefined) params.append('limit', filters.limit.toString())
    
    const response = await api.get(`/map/activity?${params.toString()}`)
    return response.data
  },

  /**
   * Get activity for a specific system
   */
  getSystemActivity: async (systemId: number, hours: number = 24): Promise<SystemActivity[]> => {
    const response = await api.get(`/map/activity/${systemId}?hours=${hours}`)
    return response.data
  },
}

