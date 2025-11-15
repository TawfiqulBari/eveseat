import React, { useState } from 'react'
import { useQuery } from '@tantml:function_calls>
import { Card } from '../components/common/Card'
import { Button } from '../components/common/Button'
import { Badge } from '../components/common/Badge'
import { useToast } from '../components/common/Toast'
import { useCharacter } from '../hooks/useCharacter'
import { analyticsService } from '../services/analytics'
import { logger } from '../utils/logger'
import { Line } from 'react-chartjs-2'

export default function MarketTrends() {
  const { characterId } = useCharacter()
  const { showToast } = useToast()
  const [typeId, setTypeId] = useState<number | null>(null)
  const [regionId, setRegionId] = useState(10000002) // The Forge
  const [period, setPeriod] = useState(30)

  const { data: trends, isLoading } = useQuery({
    queryKey: ['market-trends', typeId, regionId, period],
    queryFn: () => analyticsService.listMarketTrends(typeId!, regionId, period),
    enabled: !!characterId && !!typeId,
  })

  const { data: summary } = useQuery({
    queryKey: ['market-trend-summary', typeId, regionId],
    queryFn: () => analyticsService.getMarketTrendSummary(typeId!, regionId),
    enabled: !!characterId && !!typeId,
  })

  const formatISK = (amount: number) => {
    if (amount >= 1e9) return `${(amount / 1e9).toFixed(2)}B ISK`
    if (amount >= 1e6) return `${(amount / 1e6).toFixed(2)}M ISK`
    if (amount >= 1e3) return `${(amount / 1e3).toFixed(2)}K ISK`
    return `${amount.toLocaleString()} ISK`
  }

  const getTrendBadge = (direction: string | null) => {
    const variants: Record<string, 'success' | 'warning' | 'danger' | 'secondary'> = {
      up: 'success',
      down: 'danger',
      stable: 'secondary',
    }
    return <Badge variant={variants[direction || ''] || 'secondary'}>{direction || 'Unknown'}</Badge>
  }

  const getVolatilityBadge = (volatility: string) => {
    const variants: Record<string, 'success' | 'warning' | 'danger' | 'secondary'> = {
      low: 'success',
      medium: 'warning',
      high: 'danger',
    }
    return <Badge variant={variants[volatility] || 'secondary'}>{volatility}</Badge>
  }

  // Prepare chart data
  const chartData = {
    labels: trends?.map(t => new Date(t.date).toLocaleDateString()) || [],
    datasets: [
      {
        label: 'Average Price',
        data: trends?.map(t => t.average_price) || [],
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.4,
      },
      {
        label: 'Highest Price',
        data: trends?.map(t => t.highest_price) || [],
        borderColor: 'rgb(34, 197, 94)',
        backgroundColor: 'rgba(34, 197, 94, 0.1)',
        tension: 0.4,
        borderDash: [5, 5],
      },
      {
        label: 'Lowest Price',
        data: trends?.map(t => t.lowest_price) || [],
        borderColor: 'rgb(239, 68, 68)',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        tension: 0.4,
        borderDash: [5, 5],
      },
    ],
  }

  if (!characterId) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Market Trends</h1>
          <p className="text-gray-400">Please select a character</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Market Trends</h1>
          <p className="text-gray-400">Analyze market price trends and patterns</p>
        </div>
      </div>

      {/* Input Section */}
      <Card title="Select Item to Analyze">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Item Type ID
            </label>
            <input
              type="number"
              value={typeId || ''}
              onChange={(e) => setTypeId(e.target.value ? parseInt(e.target.value) : null)}
              className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
              placeholder="Enter type ID..."
            />
            <p className="text-xs text-gray-400 mt-1">
              Examples: 34 (Tritanium), 35 (Pyerite), 44992 (PLEX)
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Region
            </label>
            <select
              value={regionId}
              onChange={(e) => setRegionId(parseInt(e.target.value))}
              className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
            >
              <option value="10000002">The Forge (Jita)</option>
              <option value="10000043">Domain (Amarr)</option>
              <option value="10000032">Sinq Laison (Dodixie)</option>
              <option value="10000042">Metropolis (Rens)</option>
              <option value="10000030">Heimatar (Hek)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Period
            </label>
            <select
              value={period}
              onChange={(e) => setPeriod(parseInt(e.target.value))}
              className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
            >
              <option value="7">7 Days</option>
              <option value="30">30 Days</option>
              <option value="90">90 Days</option>
              <option value="180">180 Days</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Summary */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Card title="Current Price">
            <div className="text-3xl font-bold text-white">
              {formatISK(summary.current_price)}
            </div>
          </Card>

          <Card title="7-Day Change">
            <div
              className={`text-3xl font-bold ${
                summary.price_change_7d >= 0 ? 'text-green-400' : 'text-red-400'
              }`}
            >
              {summary.price_change_7d >= 0 ? '+' : ''}
              {summary.price_change_7d.toFixed(2)}%
            </div>
          </Card>

          <Card title="30-Day Change">
            <div
              className={`text-3xl font-bold ${
                summary.price_change_30d >= 0 ? 'text-green-400' : 'text-red-400'
              }`}
            >
              {summary.price_change_30d >= 0 ? '+' : ''}
              {summary.price_change_30d.toFixed(2)}%
            </div>
          </Card>

          <Card title="Volatility">
            <div className="text-2xl font-bold text-white mb-2">
              {getVolatilityBadge(summary.volatility)}
            </div>
            <div className="text-sm text-gray-400">
              Trend: {getTrendBadge(summary.trend_direction)}
            </div>
          </Card>
        </div>
      )}

      {/* Price Chart */}
      {trends && trends.length > 0 && (
        <Card title="Price History">
          <div className="h-96">
            <Line
              data={chartData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                  y: {
                    ticks: {
                      callback: (value) => formatISK(Number(value)),
                      color: 'rgb(156, 163, 175)',
                    },
                    grid: {
                      color: 'rgba(75, 85, 99, 0.3)',
                    },
                  },
                  x: {
                    ticks: {
                      color: 'rgb(156, 163, 175)',
                    },
                    grid: {
                      color: 'rgba(75, 85, 99, 0.3)',
                    },
                  },
                },
                plugins: {
                  legend: {
                    labels: {
                      color: 'rgb(156, 163, 175)',
                    },
                  },
                },
              }}
            />
          </div>
        </Card>
      )}

      {/* Volume Statistics */}
      {summary && (
        <Card title="Volume Statistics">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <div className="text-sm text-gray-400">7-Day Volume</div>
              <div className="text-2xl font-bold text-white">
                {summary.volume_7d.toLocaleString()} units
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-400">30-Day Volume</div>
              <div className="text-2xl font-bold text-white">
                {summary.volume_30d.toLocaleString()} units
              </div>
            </div>
          </div>
        </Card>
      )}

      {isLoading && typeId && (
        <Card title="Loading">
          <div className="text-gray-400">Loading market trend data...</div>
        </Card>
      )}

      {!typeId && (
        <Card title="No Item Selected">
          <div className="text-center py-8 text-gray-400">
            Enter an item type ID above to view market trends
          </div>
        </Card>
      )}
    </div>
  )
}
