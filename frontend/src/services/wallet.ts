/**
 * Wallet API Service
 */
import api from './api';

export interface WalletJournalEntry {
  id: number;
  entry_id: number;
  date: string;
  ref_type: string;
  amount: number;
  balance: number | null;
  description: string;
  first_party_id: number | null;
  second_party_id: number | null;
}

export interface WalletTransaction {
  id: number;
  transaction_id: number;
  date: string;
  type_id: number;
  quantity: number;
  unit_price: number;
  is_buy: boolean;
  client_id: number;
  location_id: number;
}

export interface WalletStatistics {
  period_days: number;
  total_income: number;
  total_expenses: number;
  net_change: number;
  market_buys: number;
  market_sells: number;
  market_profit: number;
}

export const walletService = {
  /**
   * Get wallet balance
   */
  getBalance: async (characterId: number) => {
    const response = await api.get(`/wallet/balance/${characterId}`);
    return response.data;
  },

  /**
   * List wallet journal entries
   */
  listJournal: async (params?: {
    character_id?: number;
    from_date?: string;
    to_date?: string;
    ref_type?: string;
    limit?: number;
    offset?: number;
  }) => {
    const response = await api.get<WalletJournalEntry[]>('/wallet/journal/', { params });
    return response.data;
  },

  /**
   * List wallet transactions
   */
  listTransactions: async (params?: {
    character_id?: number;
    from_date?: string;
    to_date?: string;
    type_id?: number;
    is_buy?: boolean;
    limit?: number;
    offset?: number;
  }) => {
    const response = await api.get<WalletTransaction[]>('/wallet/transactions/', { params });
    return response.data;
  },

  /**
   * Get wallet statistics
   */
  getStatistics: async (characterId: number, days: number = 30) => {
    const response = await api.get<WalletStatistics>(`/wallet/statistics/${characterId}`, {
      params: { days },
    });
    return response.data;
  },

  /**
   * Trigger wallet sync
   */
  triggerSync: async (characterId: number) => {
    const response = await api.post(`/wallet/sync/${characterId}`);
    return response.data;
  },
};
