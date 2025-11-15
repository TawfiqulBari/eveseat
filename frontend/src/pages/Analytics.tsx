import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Button } from '../components/common/Button'
import { useToast } from '../components/common/Toast'
import { useCharacter } from '../hooks/useCharacter'
import { analyticsService, AnalyticsDashboard } from '../services/analytics'
import { logger } from '../utils/logger'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

export default function Analytics() {
  const { characterId } = useCharacter()
  const { showToast } = useToast()
  const [period, setPeriod] = useState(30)

  const { data: dashboard, isLoading, error } = useQuery({
    queryKey: ['analytics-dashboard', characterId, period],
    queryFn: () => analyticsService.getDashboard(characterId!, period),
    enabled: !!characterId,
  })

  const { data: profitLossSummary } = useQuery({
    queryKey: ['profit-loss-summary', characterId, period],
    queryFn: () => analyticsService.getProfitLossSummary(characterId!, period),
    enabled: !!characterId,
  })

  const { data: portfolioSnapshots } = useQuery({
    queryKey: ['portfolio-snapshots', characterId, period],
    queryFn: () => analyticsService.listPortfolioSnapshots(characterId!, period),
    enabled: !!characterId,
  })

  const formatISK = (amount: number) => {
    if (amount >= 1e9) return `${(amount / 1e9).toFixed(2)}B ISK`
    if (amount >= 1e6) return `${(amount / 1e6).toFixed(2)}M ISK`
    if (amount >= 1e3) return `${(amount / 1e3).toFixed(2)}K ISK`
    return `${amount.toLocaleString()} ISK`
  }

  if (!characterId) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Analytics Dashboard</h1>
          <p className="text-gray-400">Please select a character</p>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Analytics Dashboard</h1>
          <p className="text-gray-400">Loading analytics data...</p>
        </div>
      </div>
    )
  }

  if (error || !dashboard) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Analytics Dashboard</h1>
          <p className="text-red-400">Failed to load analytics data</p>
        </div>
      </div>
    )
  }

  // Prepare net worth chart data
  const netWorthChartData = {
    labels: portfolioSnapshots?.map(s => new Date(s.snapshot_date).toLocaleDateString()) || [],
    datasets: [
      {
        label: 'Net Worth',
        data: portfolioSnapshots?.map(s => s.total_net_worth) || [],
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.4,
      },
    ],
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Analytics Dashboard</h1>
          <p className="text-gray-400">Comprehensive financial analytics and insights</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant={period === 7 ? 'primary' : 'secondary'}
            onClick={() => setPeriod(7)}
          >
            7 Days
          </Button>
          <Button
            variant={period === 30 ? 'primary' : 'secondary'}
            onClick={() => setPeriod(30)}
          >
            30 Days
          </Button>
          <Button
            variant={period === 90 ? 'primary' : 'secondary'}
            onClick={() => setPeriod(90)}
          >
            90 Days
          </Button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card title="Net Worth">
          <div className="text-3xl font-bold text-green-400">
            {formatISK(dashboard.portfolio.net_worth)}
          </div>
          <div className={`text-sm mt-2 ${
            dashboard.portfolio.net_worth_change >= 0 ? 'text-green-400' : 'text-red-400'
          }`}>
            {dashboard.portfolio.net_worth_change >= 0 ? '+' : ''}
            {formatISK(dashboard.portfolio.net_worth_change)}
          </div>
        </Card>

        <Card title="Net Profit ({period}d)">
          <div className={`text-3xl font-bold ${
            dashboard.profit_loss.net_profit >= 0 ? 'text-green-400' : 'text-red-400'
          }`}>
            {formatISK(dashboard.profit_loss.net_profit)}
          </div>
          <div className="text-sm mt-2 text-gray-400">
            Daily: {formatISK(dashboard.profit_loss.daily_average)}
          </div>
        </Card>

        <Card title="Total Income">
          <div className="text-3xl font-bold text-blue-400">
            {formatISK(dashboard.profit_loss.total_income)}
          </div>
          <div className="text-sm mt-2 text-gray-400">
            {period} days
          </div>
        </Card>

        <Card title="Total Expenses">
          <div className="text-3xl font-bold text-orange-400">
            {formatISK(dashboard.profit_loss.total_expenses)}
          </div>
          <div className="text-sm mt-2 text-gray-400">
            {period} days
          </div>
        </Card>
      </div>

      {/* Net Worth Chart */}
      {portfolioSnapshots && portfolioSnapshots.length > 0 && (
        <Card title="Net Worth Over Time">
          <div className="h-64">
            <Line
              data={netWorthChartData}
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

      {/* Income & Expenses Breakdown */}
      {profitLossSummary && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card title="Income by Source">
            <div className="space-y-3">
              {Object.entries(profitLossSummary.income_by_source).map(([source, amount]) => (
                <div key={source} className="flex justify-between items-center">
                  <span className="text-gray-300 capitalize">{source}</span>
                  <span className="text-green-400 font-medium">{formatISK(amount)}</span>
                </div>
              ))}
            </div>
          </Card>

          <Card title="Expenses by Source">
            <div className="space-y-3">
              {Object.entries(profitLossSummary.expenses_by_source).map(([source, amount]) => (
                <div key={source} className="flex justify-between items-center">
                  <span className="text-gray-300 capitalize">{source}</span>
                  <span className="text-red-400 font-medium">{formatISK(amount)}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* Industry Profitability */}
      {dashboard.industry.total_jobs > 0 && (
        <Card title="Industry Performance">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <div className="text-sm text-gray-400">Total Jobs</div>
              <div className="text-2xl font-bold text-white">{dashboard.industry.total_jobs}</div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Total Profit</div>
              <div className="text-2xl font-bold text-green-400">
                {formatISK(dashboard.industry.total_profit)}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Average Margin</div>
              <div className="text-2xl font-bold text-blue-400">
                {dashboard.industry.average_margin.toFixed(1)}%
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Portfolio Details */}
      <Card title="Portfolio Breakdown">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-gray-300">Wallet Balance</span>
              <span className="text-white font-medium">
                {formatISK(dashboard.portfolio.wallet_balance)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-300">Total Assets</span>
              <span className="text-white font-medium">
                {formatISK(dashboard.portfolio.total_assets)}
              </span>
            </div>
            <div className="flex justify-between items-center border-t border-eve-gray pt-3">
              <span className="text-gray-300 font-bold">Total Net Worth</span>
              <span className="text-green-400 font-bold">
                {formatISK(dashboard.portfolio.net_worth)}
              </span>
            </div>
          </div>
        </div>
      </Card>
    </div>
  )
}
