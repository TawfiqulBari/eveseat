import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Table } from '../components/common/Table'
import { Button } from '../components/common/Button'
import { TableSkeleton } from '../components/common/Skeleton'
import { useToast } from '../components/common/Toast'
import { incursionsService, Incursion } from '../services/incursions'
import { logger } from '../utils/logger'

export default function Incursions() {
  const queryClient = useQueryClient()
  const { showToast } = useToast()
  const [selectedIncursion, setSelectedIncursion] = useState<Incursion | null>(
    null
  )

  const { data: incursions, isLoading, error } = useQuery({
    queryKey: ['incursions'],
    queryFn: () => incursionsService.listIncursions(true),
  })

  const { data: summary } = useQuery({
    queryKey: ['incursions-summary'],
    queryFn: () => incursionsService.getIncursionSummary(),
  })

  const { data: statistics } = useQuery({
    queryKey: ['incursion-statistics', selectedIncursion?.constellation_id],
    queryFn: () =>
      incursionsService.getIncursionStatistics(
        selectedIncursion!.constellation_id
      ),
    enabled: !!selectedIncursion,
  })

  const syncMutation = useMutation({
    mutationFn: () => incursionsService.syncIncursions(),
    onSuccess: () => {
      showToast('Incursions sync started', 'success')
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['incursions'] })
        queryClient.invalidateQueries({ queryKey: ['incursions-summary'] })
      }, 3000)
    },
    onError: (error) => {
      logger.error('Failed to sync incursions', error)
      showToast('Failed to sync incursions', 'error')
    },
  })

  const formatISK = (amount: number) => {
    if (amount >= 1e9) return `${(amount / 1e9).toFixed(2)}B ISK`
    if (amount >= 1e6) return `${(amount / 1e6).toFixed(2)}M ISK`
    if (amount >= 1e3) return `${(amount / 1e3).toFixed(2)}K ISK`
    return `${amount.toLocaleString()} ISK`
  }

  const getStateColor = (state: string) => {
    switch (state) {
      case 'mobilizing':
        return 'bg-yellow-900 text-yellow-200'
      case 'established':
        return 'bg-red-900 text-red-200'
      case 'withdrawing':
        return 'bg-blue-900 text-blue-200'
      default:
        return 'bg-gray-700 text-gray-300'
    }
  }

  const columns = [
    {
      key: 'constellation',
      header: 'Constellation ID',
      sortable: true,
      sortKey: (incursion: Incursion) => incursion.constellation_id,
      render: (incursion: Incursion) => (
        <span className="text-white font-mono">
          {incursion.constellation_id}
        </span>
      ),
    },
    {
      key: 'state',
      header: 'State',
      sortable: true,
      sortKey: (incursion: Incursion) => incursion.state,
      render: (incursion: Incursion) => (
        <span
          className={`px-2 py-1 rounded text-xs font-medium capitalize ${getStateColor(
            incursion.state
          )}`}
        >
          {incursion.state}
        </span>
      ),
    },
    {
      key: 'influence',
      header: 'Influence',
      sortable: true,
      sortKey: (incursion: Incursion) => incursion.influence,
      render: (incursion: Incursion) => (
        <div className="w-full">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-gray-400">
              {(incursion.influence * 100).toFixed(1)}%
            </span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2">
            <div
              className="bg-red-500 h-2 rounded-full"
              style={{ width: `${incursion.influence * 100}%` }}
            />
          </div>
        </div>
      ),
    },
    {
      key: 'boss',
      header: 'Boss',
      sortable: true,
      sortKey: (incursion: Incursion) => incursion.has_boss,
      render: (incursion: Incursion) => (
        <span
          className={`px-2 py-1 rounded text-xs font-medium ${
            incursion.has_boss
              ? 'bg-purple-900 text-purple-200'
              : 'bg-gray-700 text-gray-400'
          }`}
        >
          {incursion.has_boss ? 'Yes' : 'No'}
        </span>
      ),
    },
    {
      key: 'type',
      header: 'Type',
      sortable: true,
      sortKey: (incursion: Incursion) => incursion.type,
      render: (incursion: Incursion) => (
        <span className="text-gray-300">{incursion.type}</span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      sortable: false,
      render: (incursion: Incursion) => (
        <Button size="sm" onClick={() => setSelectedIncursion(incursion)}>
          View Stats
        </Button>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Incursions</h1>
          <p className="text-gray-400">Track active Sansha incursions</p>
        </div>
        <Button
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
        >
          {syncMutation.isPending ? 'Syncing...' : 'Sync Incursions'}
        </Button>
      </div>

      {/* Summary Statistics */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
          <Card title="Total Active">
            <div className="text-3xl font-bold text-white">
              {summary.total_active}
            </div>
          </Card>

          <Card title="Established">
            <div className="text-3xl font-bold text-red-400">
              {summary.total_established}
            </div>
          </Card>

          <Card title="Withdrawing">
            <div className="text-3xl font-bold text-blue-400">
              {summary.total_withdrawing}
            </div>
          </Card>

          <Card title="With Boss">
            <div className="text-3xl font-bold text-purple-400">
              {summary.incursions_with_boss}
            </div>
          </Card>

          <Card title="Highest Influence">
            <div className="text-3xl font-bold text-orange-400">
              {(summary.highest_influence * 100).toFixed(1)}%
            </div>
          </Card>
        </div>
      )}

      {/* Incursion Statistics */}
      {selectedIncursion && statistics && (
        <Card title={`Constellation ${selectedIncursion.constellation_id} Statistics`}>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-4">
            <div>
              <div className="text-sm text-gray-400">Sites Completed</div>
              <div className="text-2xl font-bold text-white">
                {statistics.total_sites_completed}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Total ISK Earned</div>
              <div className="text-2xl font-bold text-green-400">
                {formatISK(statistics.total_isk_earned)}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Participants</div>
              <div className="text-2xl font-bold text-blue-400">
                {statistics.unique_participants}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Avg ISK/Site</div>
              <div className="text-2xl font-bold text-purple-400">
                {formatISK(statistics.average_isk_per_site)}
              </div>
            </div>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setSelectedIncursion(null)}
          >
            Close Stats
          </Button>
        </Card>
      )}

      {/* Incursions Table */}
      <Card title="Active Incursions">
        {isLoading ? (
          <TableSkeleton rows={5} columns={6} />
        ) : error ? (
          <div className="text-center py-8 text-red-400">
            Error loading incursions. Try syncing first.
          </div>
        ) : (
          <Table
            data={incursions || []}
            columns={columns}
            keyExtractor={(item) => item.id.toString()}
            emptyMessage="No active incursions found."
            defaultSort={{ key: 'influence', direction: 'desc' }}
          />
        )}
      </Card>
    </div>
  )
}
