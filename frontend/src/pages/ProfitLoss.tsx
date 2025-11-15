import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Table } from '../components/common/Table'
import { Button } from '../components/common/Button'
import { TableSkeleton } from '../components/common/Skeleton'
import { useToast } from '../components/common/Toast'
import { useCharacter } from '../hooks/useCharacter'
import { analyticsService, ProfitLoss as ProfitLossType } from '../services/analytics'
import { logger } from '../utils/logger'
import { format } from 'date-fns'

export default function ProfitLoss() {
  const { characterId } = useCharacter()
  const queryClient = useQueryClient()
  const { showToast } = useToast()
  const [period, setPeriod] = useState(30)

  const { data: records, isLoading, error } = useQuery({
    queryKey: ['profit-loss', characterId, period],
    queryFn: () =>
      analyticsService.listProfitLoss({
        character_id: characterId!,
      }),
    enabled: !!characterId,
  })

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['profit-loss-summary', characterId, period],
    queryFn: () => analyticsService.getProfitLossSummary(characterId!, period),
    enabled: !!characterId,
  })

  const calculateMutation = useMutation({
    mutationFn: () => analyticsService.triggerProfitLossCalculation(characterId!, period),
    onSuccess: () => {
      showToast('Profit/loss calculation started', 'success')
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['profit-loss'] })
        queryClient.invalidateQueries({ queryKey: ['profit-loss-summary'] })
      }, 3000)
    },
    onError: (error) => {
      logger.error('Failed to calculate profit/loss', error)
      showToast('Failed to calculate profit/loss', 'error')
    },
  })

  const formatISK = (amount: number) => {
    if (amount >= 1e9) return `${(amount / 1e9).toFixed(2)}B`
    if (amount >= 1e6) return `${(amount / 1e6).toFixed(2)}M`
    if (amount >= 1e3) return `${(amount / 1e3).toFixed(2)}K`
    return amount.toLocaleString()
  }

  const columns = [
    {
      key: 'date',
      header: 'Date',
      sortable: true,
      sortKey: (record: ProfitLossType) => new Date(record.date),
      render: (record: ProfitLossType) => (
        <span className="text-white">
          {format(new Date(record.date), 'MMM dd, yyyy')}
        </span>
      ),
    },
    {
      key: 'income',
      header: 'Total Income',
      sortable: true,
      sortKey: (record: ProfitLossType) => record.total_income,
      render: (record: ProfitLossType) => (
        <span className="text-green-400 font-medium">
          +{formatISK(record.total_income)} ISK
        </span>
      ),
    },
    {
      key: 'expenses',
      header: 'Total Expenses',
      sortable: true,
      sortKey: (record: ProfitLossType) => record.total_expenses,
      render: (record: ProfitLossType) => (
        <span className="text-red-400 font-medium">
          -{formatISK(record.total_expenses)} ISK
        </span>
      ),
    },
    {
      key: 'profit',
      header: 'Net Profit',
      sortable: true,
      sortKey: (record: ProfitLossType) => record.net_profit,
      render: (record: ProfitLossType) => (
        <span
          className={`font-bold ${
            record.net_profit >= 0 ? 'text-green-400' : 'text-red-400'
          }`}
        >
          {record.net_profit >= 0 ? '+' : ''}
          {formatISK(record.net_profit)} ISK
        </span>
      ),
    },
    {
      key: 'breakdown',
      header: 'Top Source',
      sortable: false,
      render: (record: ProfitLossType) => {
        const sources = [
          { name: 'Bounty', value: record.bounty_income },
          { name: 'Mission', value: record.mission_income },
          { name: 'Market', value: record.market_income },
          { name: 'Contract', value: record.contract_income },
          { name: 'Industry', value: record.industry_income },
        ]
        const topSource = sources.reduce((max, s) => (s.value > max.value ? s : max))

        return (
          <div className="text-sm">
            <div className="text-gray-300">{topSource.name}</div>
            <div className="text-xs text-gray-400">
              {formatISK(topSource.value)} ISK
            </div>
          </div>
        )
      },
    },
  ]

  if (!characterId) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Profit & Loss</h1>
          <p className="text-gray-400">Please select a character</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Profit & Loss</h1>
          <p className="text-gray-400">Track income and expenses</p>
        </div>
        <div className="flex gap-2">
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
          <Button
            onClick={() => calculateMutation.mutate()}
            disabled={calculateMutation.isPending}
          >
            {calculateMutation.isPending ? 'Calculating...' : 'Recalculate'}
          </Button>
        </div>
      </div>

      {/* Summary Statistics */}
      {summaryLoading ? (
        <Card title="Summary">
          <div className="text-gray-400">Loading summary...</div>
        </Card>
      ) : summary ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Card title="Net Profit">
            <div
              className={`text-3xl font-bold ${
                summary.net_profit >= 0 ? 'text-green-400' : 'text-red-400'
              }`}
            >
              {summary.net_profit >= 0 ? '+' : ''}
              {formatISK(summary.net_profit)} ISK
            </div>
            <div className="text-sm mt-2 text-gray-400">
              Daily: {formatISK(summary.daily_average)} ISK
            </div>
          </Card>

          <Card title="Total Income">
            <div className="text-3xl font-bold text-green-400">
              {formatISK(summary.total_income)} ISK
            </div>
          </Card>

          <Card title="Total Expenses">
            <div className="text-3xl font-bold text-red-400">
              {formatISK(summary.total_expenses)} ISK
            </div>
          </Card>

          <Card title="Best Day">
            <div className="text-xl font-bold text-white">
              {summary.best_day
                ? format(new Date(summary.best_day), 'MMM dd')
                : 'N/A'}
            </div>
            <div className="text-sm mt-2 text-green-400">
              +{formatISK(summary.best_day_profit)} ISK
            </div>
          </Card>
        </div>
      ) : null}

      {/* Income Breakdown */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card title="Income by Source">
            <div className="space-y-3">
              {Object.entries(summary.income_by_source)
                .sort(([, a], [, b]) => b - a)
                .map(([source, amount]) => (
                  <div key={source} className="flex justify-between items-center">
                    <span className="text-gray-300 capitalize">{source}</span>
                    <div className="text-right">
                      <div className="text-green-400 font-medium">
                        +{formatISK(amount)} ISK
                      </div>
                      <div className="text-xs text-gray-400">
                        {((amount / summary.total_income) * 100).toFixed(1)}%
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          </Card>

          <Card title="Expenses by Source">
            <div className="space-y-3">
              {Object.entries(summary.expenses_by_source)
                .sort(([, a], [, b]) => b - a)
                .map(([source, amount]) => (
                  <div key={source} className="flex justify-between items-center">
                    <span className="text-gray-300 capitalize">{source}</span>
                    <div className="text-right">
                      <div className="text-red-400 font-medium">
                        -{formatISK(amount)} ISK
                      </div>
                      <div className="text-xs text-gray-400">
                        {((amount / summary.total_expenses) * 100).toFixed(1)}%
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          </Card>
        </div>
      )}

      {/* Daily Records Table */}
      <Card title={`Daily Profit/Loss (${period} days)`}>
        {isLoading ? (
          <TableSkeleton rows={10} columns={5} />
        ) : error ? (
          <div className="text-center py-8 text-red-400">
            Error loading profit/loss data. Try recalculating.
          </div>
        ) : (
          <Table
            data={records || []}
            columns={columns}
            keyExtractor={(item) => item.id.toString()}
            emptyMessage="No profit/loss data found. Click 'Recalculate' to analyze your wallet data."
            defaultSort={{ key: 'date', direction: 'desc' }}
          />
        )}
      </Card>
    </div>
  )
}
