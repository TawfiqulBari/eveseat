/**
 * Analytics API service
 */
import axios from 'axios'

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000'

export interface MarketTrend {
  id: number
  type_id: number
  region_id: number
  date: string
  average_price: number | null
  highest_price: number | null
  lowest_price: number | null
  median_price: number | null
  volume: number | null
  price_change_percent: number | null
  trend_direction: string | null
}

export interface ProfitLoss {
  id: number
  character_id: number
  date: string
  total_income: number
  total_expenses: number
  net_profit: number
  bounty_income: number
  mission_income: number
  market_income: number
  contract_income: number
  industry_income: number
  market_expenses: number
  ship_losses: number
}

export interface ProfitLossSummary {
  total_income: number
  total_expenses: number
  net_profit: number
  income_by_source: { [key: string]: number }
  expenses_by_source: { [key: string]: number }
  daily_average: number
  best_day: string | null
  best_day_profit: number
}

export interface IndustryProfitability {
  id: number
  character_id: number
  product_type_id: number
  product_quantity: number
  blueprint_type_id: number
  total_cost: number
  estimated_revenue: number
  estimated_profit: number
  estimated_margin_percent: number
  job_type: string | null
  isk_per_hour: number
}

export interface IndustryProfitabilitySummary {
  total_jobs: number
  profitable_jobs: number
  total_profit: number
  average_margin: number
  best_product_type_id: number
  best_product_margin: number
}

export interface ISKFlow {
  id: number
  character_id: number
  date: string
  amount: number
  flow_type: string
  category: string
  description: string | null
}

export interface ISKFlowSummary {
  total_income: number
  total_expenses: number
  income_by_category: { [key: string]: number }
  expense_by_category: { [key: string]: number }
  net_flow: number
}

export interface PortfolioSnapshot {
  id: number
  character_id: number
  snapshot_date: string
  wallet_balance: number
  total_assets_value: number
  total_net_worth: number
  net_worth_change: number
  net_worth_change_percent: number
}

export interface TradingOpportunity {
  id: number
  type_id: number
  buy_location_id: number
  sell_location_id: number
  buy_price: number
  sell_price: number
  profit_per_unit: number
  profit_margin_percent: number
  potential_volume: number
  required_capital: number
  jumps: number | null
  risk_level: string | null
}

export interface MarketTrendSummary {
  type_id: number
  current_price: number
  price_change_7d: number
  price_change_30d: number
  volume_7d: number
  volume_30d: number
  trend_direction: string
  volatility: string
}

export interface AnalyticsDashboard {
  character_id: number
  period_days: number
  profit_loss: {
    total_income: number
    total_expenses: number
    net_profit: number
    daily_average: number
  }
  portfolio: {
    net_worth: number
    net_worth_change: number
    wallet_balance: number
    total_assets: number
  }
  industry: {
    total_jobs: number
    total_profit: number
    average_margin: number
  }
}

const getAuthHeader = () => {
  const token = localStorage.getItem('access_token')
  return {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  }
}

export const analyticsService = {
  // Profit/Loss endpoints
  async listProfitLoss(params: {
    character_id: number
    start_date?: string
    end_date?: string
    limit?: number
    offset?: number
  }): Promise<ProfitLoss[]> {
    const response = await axios.get(`${API_BASE_URL}/analytics/profit-loss`, {
      params,
      ...getAuthHeader(),
    })
    return response.data
  },

  async getProfitLossSummary(characterId: number, days: number = 30): Promise<ProfitLossSummary> {
    const response = await axios.get(
      `${API_BASE_URL}/analytics/profit-loss/summary`,
      {
        params: { character_id: characterId, days },
        ...getAuthHeader(),
      }
    )
    return response.data
  },

  async triggerProfitLossCalculation(characterId: number, days: number = 30): Promise<void> {
    await axios.post(
      `${API_BASE_URL}/analytics/profit-loss/calculate/${characterId}`,
      {},
      { params: { days }, ...getAuthHeader() }
    )
  },

  // ISK Flow endpoints
  async listISKFlow(params: {
    character_id: number
    flow_type?: string
    category?: string
    start_date?: string
    end_date?: string
    limit?: number
    offset?: number
  }): Promise<ISKFlow[]> {
    const response = await axios.get(`${API_BASE_URL}/analytics/isk-flow`, {
      params,
      ...getAuthHeader(),
    })
    return response.data
  },

  async getISKFlowSummary(characterId: number, days: number = 30): Promise<ISKFlowSummary> {
    const response = await axios.get(`${API_BASE_URL}/analytics/isk-flow/summary`, {
      params: { character_id: characterId, days },
      ...getAuthHeader(),
    })
    return response.data
  },

  async triggerISKFlowAggregation(characterId: number, days: number = 30): Promise<void> {
    await axios.post(
      `${API_BASE_URL}/analytics/isk-flow/aggregate/${characterId}`,
      {},
      { params: { days }, ...getAuthHeader() }
    )
  },

  // Industry Profitability endpoints
  async listIndustryProfitability(params: {
    character_id: number
    job_type?: string
    product_type_id?: number
    limit?: number
    offset?: number
  }): Promise<IndustryProfitability[]> {
    const response = await axios.get(`${API_BASE_URL}/analytics/industry/profitability`, {
      params,
      ...getAuthHeader(),
    })
    return response.data
  },

  async getIndustryProfitabilitySummary(
    characterId: number,
    days: number = 30
  ): Promise<IndustryProfitabilitySummary> {
    const response = await axios.get(
      `${API_BASE_URL}/analytics/industry/profitability/summary`,
      {
        params: { character_id: characterId, days },
        ...getAuthHeader(),
      }
    )
    return response.data
  },

  async triggerIndustryProfitabilityCalculation(characterId: number): Promise<void> {
    await axios.post(
      `${API_BASE_URL}/analytics/industry/profitability/calculate/${characterId}`,
      {},
      getAuthHeader()
    )
  },

  // Market Trends endpoints
  async listMarketTrends(
    typeId: number,
    regionId: number = 10000002,
    days: number = 30
  ): Promise<MarketTrend[]> {
    const response = await axios.get(`${API_BASE_URL}/analytics/market/trends`, {
      params: { type_id: typeId, region_id: regionId, days },
      ...getAuthHeader(),
    })
    return response.data
  },

  async getMarketTrendSummary(
    typeId: number,
    regionId: number = 10000002
  ): Promise<MarketTrendSummary> {
    const response = await axios.get(`${API_BASE_URL}/analytics/market/trends/summary`, {
      params: { type_id: typeId, region_id: regionId },
      ...getAuthHeader(),
    })
    return response.data
  },

  async triggerMarketTrendCalculation(
    typeIds: number[],
    regionId: number = 10000002
  ): Promise<void> {
    await axios.post(
      `${API_BASE_URL}/analytics/market/trends/calculate`,
      {},
      {
        params: { type_ids: typeIds, region_id: regionId },
        ...getAuthHeader(),
      }
    )
  },

  // Trading Opportunities endpoints
  async listTradingOpportunities(params: {
    min_profit_margin?: number
    max_capital?: number
    risk_level?: string
    limit?: number
  }): Promise<TradingOpportunity[]> {
    const response = await axios.get(`${API_BASE_URL}/analytics/trading/opportunities`, {
      params,
      ...getAuthHeader(),
    })
    return response.data
  },

  async triggerFindTradingOpportunities(regionIds: number[]): Promise<void> {
    await axios.post(
      `${API_BASE_URL}/analytics/trading/opportunities/find`,
      {},
      {
        params: { region_ids: regionIds },
        ...getAuthHeader(),
      }
    )
  },

  // Portfolio endpoints
  async listPortfolioSnapshots(characterId: number, days: number = 30): Promise<PortfolioSnapshot[]> {
    const response = await axios.get(`${API_BASE_URL}/analytics/portfolio/snapshots`, {
      params: { character_id: characterId, days },
      ...getAuthHeader(),
    })
    return response.data
  },

  async triggerPortfolioSnapshot(characterId: number): Promise<void> {
    await axios.post(
      `${API_BASE_URL}/analytics/portfolio/snapshot/${characterId}`,
      {},
      getAuthHeader()
    )
  },

  // Analytics Dashboard
  async getDashboard(characterId: number, days: number = 30): Promise<AnalyticsDashboard> {
    const response = await axios.get(
      `${API_BASE_URL}/analytics/dashboard/${characterId}`,
      {
        params: { days },
        ...getAuthHeader(),
      }
    )
    return response.data
  },
}
