import React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Table } from '../components/common/Table'
import { Button } from '../components/common/Button'
import { Badge } from '../components/common/Badge'
import { TableSkeleton } from '../components/common/Skeleton'
import { useToast } from '../components/common/Toast'
import { useCharacter } from '../hooks/useCharacter'
import { analyticsService, IndustryProfitability } from '../services/analytics'
import { logger } from '../utils/logger'

export default function IndustryCalculator() {
  const { characterId } = useCharacter()
  const queryClient = useQueryClient()
  const { showToast } = useToast()

  const { data: profitability, isLoading, error } = useQuery({
    queryKey: ['industry-profitability', characterId],
    queryFn: () =>
      analyticsService.listIndustryProfitability({
        character_id: characterId!,
      }),
    enabled: !!characterId,
  })

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['industry-profitability-summary', characterId],
    queryFn: () => analyticsService.getIndustryProfitabilitySummary(characterId!, 90),
    enabled: !!characterId,
  })

  const calculateMutation = useMutation({
    mutationFn: () => analyticsService.triggerIndustryProfitabilityCalculation(characterId!),
    onSuccess: () => {
      showToast('Industry profitability calculation started', 'success')
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['industry-profitability'] })
        queryClient.invalidateQueries({ queryKey: ['industry-profitability-summary'] })
      }, 3000)
    },
    onError: (error) => {
      logger.error('Failed to calculate industry profitability', error)
      showToast('Failed to calculate industry profitability', 'error')
    },
  })

  const formatISK = (amount: number) => {
    if (amount >= 1e9) return `${(amount / 1e9).toFixed(2)}B`
    if (amount >= 1e6) return `${(amount / 1e6).toFixed(2)}M`
    if (amount >= 1e3) return `${(amount / 1e3).toFixed(2)}K`
    return amount.toLocaleString()
  }

  const getMarginBadge = (margin: number) => {
    if (margin >= 20) return <Badge variant="success">{margin.toFixed(1)}%</Badge>
    if (margin >= 10) return <Badge variant="info">{margin.toFixed(1)}%</Badge>
    if (margin >= 0) return <Badge variant="warning">{margin.toFixed(1)}%</Badge>
    return <Badge variant="danger">{margin.toFixed(1)}%</Badge>
  }

  const columns = [
    {
      key: 'product',
      header: 'Product',
      sortable: true,
      sortKey: (item: IndustryProfitability) => item.product_type_id,
      render: (item: IndustryProfitability) => (
        <div>
          <div className="text-white">Type {item.product_type_id}</div>
          <div className="text-xs text-gray-400">{item.product_quantity} units</div>
        </div>
      ),
    },
    {
      key: 'type',
      header: 'Job Type',
      sortable: true,
      sortKey: (item: IndustryProfitability) => item.job_type || '',
      render: (item: IndustryProfitability) => (
        <span className="text-gray-300 capitalize">
          {item.job_type?.replace('_', ' ') || 'Unknown'}
        </span>
      ),
    },
    {
      key: 'cost',
      header: 'Total Cost',
      sortable: true,
      sortKey: (item: IndustryProfitability) => item.total_cost,
      render: (item: IndustryProfitability) => (
        <span className="text-red-400">{formatISK(item.total_cost)} ISK</span>
      ),
    },
    {
      key: 'revenue',
      header: 'Est. Revenue',
      sortable: true,
      sortKey: (item: IndustryProfitability) => item.estimated_revenue,
      render: (item: IndustryProfitability) => (
        <span className="text-green-400">{formatISK(item.estimated_revenue)} ISK</span>
      ),
    },
    {
      key: 'profit',
      header: 'Est. Profit',
      sortable: true,
      sortKey: (item: IndustryProfitability) => item.estimated_profit,
      render: (item: IndustryProfitability) => (
        <span
          className={`font-medium ${
            item.estimated_profit >= 0 ? 'text-green-400' : 'text-red-400'
          }`}
        >
          {item.estimated_profit >= 0 ? '+' : ''}
          {formatISK(item.estimated_profit)} ISK
        </span>
      ),
    },
    {
      key: 'margin',
      header: 'Margin',
      sortable: true,
      sortKey: (item: IndustryProfitability) => item.estimated_margin_percent,
      render: (item: IndustryProfitability) => getMarginBadge(item.estimated_margin_percent),
    },
    {
      key: 'iskPerHour',
      header: 'ISK/Hour',
      sortable: true,
      sortKey: (item: IndustryProfitability) => item.isk_per_hour,
      render: (item: IndustryProfitability) => (
        <span className="text-blue-400">{formatISK(item.isk_per_hour)} ISK/h</span>
      ),
    },
  ]

  if (!characterId) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Industry Calculator</h1>
          <p className="text-gray-400">Please select a character</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Industry Calculator</h1>
          <p className="text-gray-400">Calculate profitability of industry jobs</p>
        </div>
        <Button
          onClick={() => calculateMutation.mutate()}
          disabled={calculateMutation.isPending}
        >
          {calculateMutation.isPending ? 'Calculating...' : 'Recalculate'}
        </Button>
      </div>

      {/* Summary Statistics */}
      {summaryLoading ? (
        <Card title="Summary">
          <div className="text-gray-400">Loading summary...</div>
        </Card>
      ) : summary ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Card title="Total Jobs">
            <div className="text-3xl font-bold text-white">{summary.total_jobs}</div>
            <div className="text-sm mt-2 text-gray-400">
              {summary.profitable_jobs} profitable
            </div>
          </Card>

          <Card title="Total Profit">
            <div
              className={`text-3xl font-bold ${
                summary.total_profit >= 0 ? 'text-green-400' : 'text-red-400'
              }`}
            >
              {summary.total_profit >= 0 ? '+' : ''}
              {formatISK(summary.total_profit)} ISK
            </div>
          </Card>

          <Card title="Average Margin">
            <div className="text-3xl font-bold text-blue-400">
              {summary.average_margin.toFixed(1)}%
            </div>
          </Card>

          <Card title="Best Product">
            <div className="text-xl font-bold text-white">
              Type {summary.best_product_type_id}
            </div>
            <div className="text-sm mt-2 text-green-400">
              {summary.best_product_margin.toFixed(1)}% margin
            </div>
          </Card>
        </div>
      ) : null}

      {/* Help Card */}
      <Card title="How It Works">
        <div className="text-gray-300 space-y-2">
          <p>
            The industry calculator analyzes your industry jobs and calculates profitability
            based on:
          </p>
          <ul className="list-disc list-inside ml-4 space-y-1 text-sm">
            <li>Material costs (based on current market prices)</li>
            <li>Installation and tax costs</li>
            <li>Time value (estimated at 10M ISK/hour)</li>
            <li>Estimated revenue (based on current market prices)</li>
          </ul>
          <p className="text-sm text-gray-400 mt-3">
            Note: Calculations are estimates. Actual profitability may vary based on market
            conditions and your specific setup.
          </p>
        </div>
      </Card>

      {/* Profitability Table */}
      <Card title="Job Profitability Analysis">
        {isLoading ? (
          <TableSkeleton rows={10} columns={7} />
        ) : error ? (
          <div className="text-center py-8 text-red-400">
            Error loading profitability data. Try recalculating.
          </div>
        ) : (
          <Table
            data={profitability || []}
            columns={columns}
            keyExtractor={(item) => item.id.toString()}
            emptyMessage="No industry jobs found. Complete some industry jobs and click 'Recalculate' to analyze profitability."
            defaultSort={{ key: 'profit', direction: 'desc' }}
          />
        )}
      </Card>

      {/* Tips Card */}
      <Card title="Optimization Tips">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-300">
          <div>
            <h4 className="font-medium text-white mb-2">Increase Profitability:</h4>
            <ul className="list-disc list-inside space-y-1">
              <li>Research material efficiency (ME) on blueprints</li>
              <li>Research time efficiency (TE) to reduce duration</li>
              <li>Use structures with bonuses</li>
              <li>Buy materials during market dips</li>
            </ul>
          </div>
          <div>
            <h4 className="font-medium text-white mb-2">Best Practices:</h4>
            <ul className="list-disc list-inside space-y-1">
              <li>Focus on high-margin products</li>
              <li>Consider ISK/hour for time efficiency</li>
              <li>Monitor market trends before starting jobs</li>
              <li>Account for taxes and fees in calculations</li>
            </ul>
          </div>
        </div>
      </Card>
    </div>
  )
}
