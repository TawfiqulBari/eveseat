/**
 * Structures API service
 */
import axios from 'axios'

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000'

export interface Structure {
  id: number
  structure_id: number
  name: string | null
  type_id: number
  system_id: number
  position_x: number | null
  position_y: number | null
  position_z: number | null
  state: string | null
  state_timer_start: string | null
  state_timer_end: string | null
  unanchors_at: string | null
  fuel_expires: string | null
  next_reinforce_hour: number | null
  next_reinforce_day: number | null
  services: any | null
  synced_at: string | null
}

export interface StructureStatistics {
  total_structures: number
  online_structures: number
  low_fuel_structures: number
  structures_by_type: { [key: string]: number }
  structures_by_system: { [key: string]: number }
}

interface ListStructuresParams {
  corporation_id?: number
  system_id?: number
  state?: string
  limit?: number
  offset?: number
}

const getAuthHeader = () => {
  const token = localStorage.getItem('access_token')
  return {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  }
}

export const structuresService = {
  async listStructures(params: ListStructuresParams): Promise<Structure[]> {
    const response = await axios.get(`${API_BASE_URL}/structures/`, {
      params,
      ...getAuthHeader(),
    })
    return response.data
  },

  async getStructure(structureId: number): Promise<Structure> {
    const response = await axios.get(`${API_BASE_URL}/structures/${structureId}`, getAuthHeader())
    return response.data
  },

  async getStatistics(corporationId: number): Promise<StructureStatistics> {
    const response = await axios.get(
      `${API_BASE_URL}/structures/statistics/${corporationId}`,
      getAuthHeader()
    )
    return response.data
  },

  async triggerSync(corporationId: number): Promise<void> {
    await axios.post(`${API_BASE_URL}/structures/sync/${corporationId}`, {}, getAuthHeader())
  },
}
