/**
 * Moon mining API service
 */
import axios from 'axios'

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000'

export interface MoonExtraction {
  id: number
  structure_id: number
  moon_id: number
  chunk_arrival_time: string
  extraction_start_time: string
  natural_decay_time: string | null
  status: string | null
  synced_at: string | null
}

export interface Moon {
  id: number
  moon_id: number
  system_id: number
  name: string | null
  composition: { [key: string]: number } | null
  estimated_value: number | null
  last_scanned: string | null
}

export interface MiningLedger {
  id: number
  character_id: number
  date: string
  type_id: number
  quantity: number
  system_id: number
}

export interface MoonExtractionStatistics {
  total_extractions: number
  active_extractions: number
  ready_extractions: number
  upcoming_arrivals: number
  extractions_by_moon: { [key: string]: number }
}

export interface MiningStatistics {
  total_miners: number
  total_quantity: number
  mining_by_character: { [key: string]: number }
  mining_by_type: { [key: string]: number }
  mining_by_system: { [key: string]: number }
}

interface ListExtractionsParams {
  corporation_id?: number
  moon_id?: number
  status?: string
  limit?: number
  offset?: number
}

interface ListMoonsParams {
  system_id?: number
  limit?: number
  offset?: number
}

interface ListLedgerParams {
  corporation_id?: number
  character_id?: number
  system_id?: number
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

export const moonsService = {
  async listExtractions(params: ListExtractionsParams): Promise<MoonExtraction[]> {
    const response = await axios.get(`${API_BASE_URL}/moons/extractions`, {
      params,
      ...getAuthHeader(),
    })
    return response.data
  },

  async getExtractionStatistics(corporationId: number): Promise<MoonExtractionStatistics> {
    const response = await axios.get(
      `${API_BASE_URL}/moons/extractions/statistics/${corporationId}`,
      getAuthHeader()
    )
    return response.data
  },

  async listMoons(params: ListMoonsParams): Promise<Moon[]> {
    const response = await axios.get(`${API_BASE_URL}/moons/moons`, {
      params,
      ...getAuthHeader(),
    })
    return response.data
  },

  async listLedger(params: ListLedgerParams): Promise<MiningLedger[]> {
    const response = await axios.get(`${API_BASE_URL}/moons/ledger`, {
      params,
      ...getAuthHeader(),
    })
    return response.data
  },

  async getLedgerStatistics(corporationId: number, days: number = 30): Promise<MiningStatistics> {
    const response = await axios.get(
      `${API_BASE_URL}/moons/ledger/statistics/${corporationId}`,
      {
        params: { days },
        ...getAuthHeader(),
      }
    )
    return response.data
  },

  async triggerExtractionSync(corporationId: number): Promise<void> {
    await axios.post(
      `${API_BASE_URL}/moons/extractions/sync/${corporationId}`,
      {},
      getAuthHeader()
    )
  },

  async triggerLedgerSync(corporationId: number): Promise<void> {
    await axios.post(`${API_BASE_URL}/moons/ledger/sync/${corporationId}`, {}, getAuthHeader())
  },
}
