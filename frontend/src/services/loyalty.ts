/**
 * Loyalty Points API Service
 */
import api from './api';

export interface LoyaltyPoint {
  id: number;
  corporation_id: number;
  loyalty_points: number;
}

export interface LoyaltyOffer {
  id: number;
  offer_id: number;
  corporation_id: number;
  type_id: number;
  quantity: number;
  lp_cost: number;
  isk_cost: number;
  required_items: string | null;
}

export interface LoyaltyStatistics {
  total_lp: number;
  total_corporations: number;
  top_corporations: Array<{
    corporation_id: number;
    loyalty_points: number;
  }>;
}

export const loyaltyService = {
  /**
   * List loyalty points
   */
  listPoints: async (params?: {
    character_id?: number;
    corporation_id?: number;
    limit?: number;
    offset?: number;
  }) => {
    const response = await api.get<LoyaltyPoint[]>('/loyalty/points/', { params });
    return response.data;
  },

  /**
   * List loyalty offers
   */
  listOffers: async (params?: {
    corporation_id?: number;
    type_id?: number;
    limit?: number;
    offset?: number;
  }) => {
    const response = await api.get<LoyaltyOffer[]>('/loyalty/offers/', { params });
    return response.data;
  },

  /**
   * Get a specific loyalty offer
   */
  getOffer: async (offerId: number) => {
    const response = await api.get<LoyaltyOffer>(`/loyalty/offers/${offerId}`);
    return response.data;
  },

  /**
   * Get loyalty statistics
   */
  getStatistics: async (characterId: number) => {
    const response = await api.get<LoyaltyStatistics>(`/loyalty/statistics/${characterId}`);
    return response.data;
  },

  /**
   * Trigger loyalty sync
   */
  triggerSync: async (characterId: number) => {
    const response = await api.post(`/loyalty/sync/${characterId}`);
    return response.data;
  },
};
