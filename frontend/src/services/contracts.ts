/**
 * Contracts API Service
 */
import api from './api';

export interface Contract {
  id: number;
  contract_id: number;
  issuer_id: number;
  type: string;
  availability: string;
  status: string;
  price: number | null;
  reward: number | null;
  collateral: number | null;
  volume: number | null;
  date_issued: string;
  date_expired: string;
  start_location_id: number | null;
  end_location_id: number | null;
}

export interface ContractItem {
  id: number;
  type_id: number;
  quantity: number;
  is_included: boolean;
  is_singleton: boolean;
}

export interface ContractDetail extends Contract {
  items: ContractItem[];
}

export const contractsService = {
  /**
   * List contracts
   */
  listContracts: async (params?: {
    character_id?: number;
    contract_type?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }) => {
    const response = await api.get<Contract[]>('/contracts/', { params });
    return response.data;
  },

  /**
   * Get contract details with items
   */
  getContract: async (contractId: number) => {
    const response = await api.get<ContractDetail>(`/contracts/${contractId}`);
    return response.data;
  },

  /**
   * Get contract items
   */
  getContractItems: async (contractId: number) => {
    const response = await api.get<ContractItem[]>(`/contracts/${contractId}/items`);
    return response.data;
  },

  /**
   * Get contract statistics
   */
  getStatistics: async (characterId: number) => {
    const response = await api.get(`/contracts/statistics/${characterId}`);
    return response.data;
  },

  /**
   * Trigger contract sync
   */
  triggerSync: async (characterId: number) => {
    const response = await api.post(`/contracts/sync/${characterId}`);
    return response.data;
  },
};
