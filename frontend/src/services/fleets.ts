import api from './api'

export interface Fleet {
  id: number
  fleet_id: number
  character_id: number
  fleet_name: string | null
  is_free_move: boolean
  is_registered: boolean
  is_voice_enabled: boolean
  motd: string | null
  fleet_data: Record<string, any> | null
  last_synced_at: string | null
}

export interface FleetMember {
  id: number
  fleet_id: number
  character_id: number
  character_name: string | null
  ship_type_id: number | null
  ship_type_name: string | null
  role: string
  role_name: string
  join_time: string
  takes_fleet_warp: boolean
}

export interface Doctrine {
  id: number
  name: string
  description: string | null
  ship_types: number[]
  is_active: boolean
  created_at: string
}

export interface DoctrineCheckRequest {
  doctrine_id: number
}

export interface DoctrineCheckResponse {
  fleet_id: number
  doctrine_id: number
  compliance: {
    total_members: number
    compliant: number
    non_compliant: number
    compliance_rate: number
  }
  members_compliant: Array<{
    character_id: number
    character_name: string
    ship_type_id: number
    ship_type_name: string
  }>
  members_non_compliant: Array<{
    character_id: number
    character_name: string
    ship_type_id: number
    ship_type_name: string
    expected_ship_types: number[]
  }>
}

export const fleetsService = {
  /**
   * List fleets for a character
   */
  list: async (characterId: number): Promise<Fleet[]> => {
    const response = await api.get(`/fleets?character_id=${characterId}`)
    return response.data
  },

  /**
   * Get fleet by ID
   */
  get: async (fleetId: number, characterId: number): Promise<Fleet> => {
    const response = await api.get(`/fleets/${fleetId}?character_id=${characterId}`)
    return response.data
  },

  /**
   * Get fleet members
   */
  getMembers: async (fleetId: number, characterId: number): Promise<FleetMember[]> => {
    const response = await api.get(`/fleets/${fleetId}/members?character_id=${characterId}`)
    return response.data
  },

  /**
   * Check fleet doctrine compliance
   */
  checkDoctrine: async (
    fleetId: number,
    characterId: number,
    doctrineId: number
  ): Promise<DoctrineCheckResponse> => {
    const response = await api.post(
      `/fleets/${fleetId}/doctrine-check?character_id=${characterId}`,
      { doctrine_id: doctrineId }
    )
    return response.data
  },

  /**
   * List doctrines
   */
  listDoctrines: async (isActive?: boolean): Promise<Doctrine[]> => {
    const params = isActive !== undefined ? `?is_active=${isActive}` : ''
    const response = await api.get(`/fleets/doctrines${params}`)
    return response.data
  },
}

