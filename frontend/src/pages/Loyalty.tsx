import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Table } from '../components/common/Table'
import { Button } from '../components/common/Button'
import { TableSkeleton } from '../components/common/Skeleton'
import { useToast } from '../components/common/Toast'
import { useCharacter } from '../hooks/useCharacter'
import { loyaltyService, LoyaltyPoint } from '../services/loyalty'
import { logger } from '../utils/logger'
import { formatISK } from '../utils/formatters'

export default function Loyalty() {
  const { characterId } = useCharacter()
  const queryClient = useQueryClient()
  const { showToast } = useToast()

  const { data: loyaltyPoints, isLoading: lpLoading, error: lpError } = useQuery({
    queryKey: ['loyalty-points', characterId],
    queryFn: () => loyaltyService.listPoints({
      character_id: characterId || undefined,
    }),
    enabled: !!characterId,
  })

  const { data: statistics, isLoading: statsLoading } = useQuery({
    queryKey: ['loyalty-statistics', characterId],
    queryFn: () => loyaltyService.getStatistics(characterId!),
    enabled: !!characterId,
  })

  const syncMutation = useMutation({
    mutationFn: () => loyaltyService.triggerSync(characterId!),
    onSuccess: () => {
      showToast('Loyalty points sync started', 'success')
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['loyalty-points'] })
        queryClient.invalidateQueries({ queryKey: ['loyalty-statistics'] })
      }, 2000)
    },
    onError: (error) => {
      logger.error('Failed to sync loyalty points', error)
      showToast('Failed to sync loyalty points', 'error')
    },
  })

  const columns = [
    {
      key: 'corporation_id',
      header: 'Corporation',
      sortable: true,
      sortKey: (lp: LoyaltyPoint) => lp.corporation_id,
      render: (lp: LoyaltyPoint) => (
        <span className="text-white font-medium">Corporation {lp.corporation_id}</span>
      ),
    },
    {
      key: 'loyalty_points',
      header: 'Loyalty Points',
      sortable: true,
      sortKey: (lp: LoyaltyPoint) => lp.loyalty_points,
      render: (lp: LoyaltyPoint) => (
        <span className="text-yellow-400 font-medium text-lg">
          {lp.loyalty_points.toLocaleString()} LP
        </span>
      ),
    },
  ]

  if (!characterId) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Loyalty Points</h1>
          <p className="text-gray-400">Please select a character</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Loyalty Points</h1>
          <p className="text-gray-400">Track your loyalty points across corporations</p>
        </div>
        <Button
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
        >
          {syncMutation.isPending ? 'Syncing...' : 'Sync LP'}
        </Button>
      </div>

      {/* Statistics */}
      {statsLoading ? (
        <Card title="LP Statistics">
          <div className="text-gray-400">Loading statistics...</div>
        </Card>
      ) : statistics ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card title="Total LP">
            <div className="text-4xl font-bold text-yellow-400">
              {statistics.total_lp.toLocaleString()}
            </div>
            <div className="text-sm text-gray-400 mt-1">Loyalty Points</div>
          </Card>
          <Card title="Corporations">
            <div className="text-4xl font-bold text-white">{statistics.total_corporations}</div>
            <div className="text-sm text-gray-400 mt-1">With LP Balance</div>
          </Card>
        </div>
      ) : null}

      {/* Top Corporations */}
      {statistics && statistics.top_corporations.length > 0 && (
        <Card title="Top 5 Corporations by LP">
          <div className="space-y-3">
            {statistics.top_corporations.map((corp, idx) => (
              <div
                key={corp.corporation_id}
                className="flex items-center justify-between p-3 bg-eve-darker rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <div className="text-2xl font-bold text-gray-500">#{idx + 1}</div>
                  <div>
                    <div className="text-white font-medium">
                      Corporation {corp.corporation_id}
                    </div>
                  </div>
                </div>
                <div className="text-yellow-400 font-medium text-lg">
                  {corp.loyalty_points.toLocaleString()} LP
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* LP Table */}
      <Card title={`Loyalty Points (${loyaltyPoints?.length || 0})`}>
        {lpLoading ? (
          <TableSkeleton rows={10} columns={2} />
        ) : lpError ? (
          <div className="text-center py-8 text-red-400">
            Error loading loyalty points. Try syncing your LP.
          </div>
        ) : (
          <Table
            data={loyaltyPoints || []}
            columns={columns}
            keyExtractor={(item) => item.id.toString()}
            emptyMessage="No loyalty points found. Click 'Sync LP' to fetch from EVE Online."
            defaultSort={{ key: 'loyalty_points', direction: 'desc' }}
          />
        )}
      </Card>
    </div>
  )
}
