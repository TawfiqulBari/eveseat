import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Table } from '../components/common/Table'
import { Button } from '../components/common/Button'
import { TableSkeleton } from '../components/common/Skeleton'
import { useToast } from '../components/common/Toast'
import { useCharacter } from '../hooks/useCharacter'
import { alliancesService, Alliance } from '../services/alliances'
import { logger } from '../utils/logger'
import { format } from 'date-fns'

export default function Alliances() {
  const { characterId } = useCharacter()
  const queryClient = useQueryClient()
  const { showToast } = useToast()
  const [selectedAlliance, setSelectedAlliance] = useState<Alliance | null>(null)

  const { data: alliances, isLoading, error } = useQuery({
    queryKey: ['alliances'],
    queryFn: () => alliancesService.listAlliances(),
  })

  const { data: statistics } = useQuery({
    queryKey: ['alliance-statistics', selectedAlliance?.alliance_id],
    queryFn: () =>
      alliancesService.getAllianceStatistics(selectedAlliance!.alliance_id),
    enabled: !!selectedAlliance,
  })

  const syncMutation = useMutation({
    mutationFn: (allianceId: number) => alliancesService.syncAlliance(allianceId),
    onSuccess: () => {
      showToast('Alliance sync started', 'success')
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['alliances'] })
      }, 3000)
    },
    onError: (error) => {
      logger.error('Failed to sync alliance', error)
      showToast('Failed to sync alliance', 'error')
    },
  })

  const columns = [
    {
      key: 'name',
      header: 'Alliance Name',
      sortable: true,
      sortKey: (alliance: Alliance) => alliance.alliance_name,
      render: (alliance: Alliance) => (
        <div>
          <div className="text-white font-medium">{alliance.alliance_name}</div>
          <div className="text-sm text-gray-400">[{alliance.ticker}]</div>
        </div>
      ),
    },
    {
      key: 'corporations',
      header: 'Corporations',
      sortable: true,
      sortKey: (alliance: Alliance) => alliance.corporation_count,
      render: (alliance: Alliance) => (
        <span className="text-white">{alliance.corporation_count.toLocaleString()}</span>
      ),
    },
    {
      key: 'members',
      header: 'Members',
      sortable: true,
      sortKey: (alliance: Alliance) => alliance.member_count,
      render: (alliance: Alliance) => (
        <span className="text-white">{alliance.member_count.toLocaleString()}</span>
      ),
    },
    {
      key: 'founded',
      header: 'Founded',
      sortable: true,
      sortKey: (alliance: Alliance) =>
        alliance.date_founded ? new Date(alliance.date_founded) : null,
      render: (alliance: Alliance) => (
        <span className="text-gray-300">
          {alliance.date_founded
            ? format(new Date(alliance.date_founded), 'MMM dd, yyyy')
            : 'Unknown'}
        </span>
      ),
    },
    {
      key: 'synced',
      header: 'Last Sync',
      sortable: true,
      sortKey: (alliance: Alliance) =>
        alliance.synced_at ? new Date(alliance.synced_at) : null,
      render: (alliance: Alliance) => (
        <span className="text-sm text-gray-400">
          {alliance.synced_at
            ? format(new Date(alliance.synced_at), 'MMM dd, HH:mm')
            : 'Never'}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      sortable: false,
      render: (alliance: Alliance) => (
        <div className="flex gap-2">
          <Button
            size="sm"
            onClick={() => setSelectedAlliance(alliance)}
          >
            View Details
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => syncMutation.mutate(alliance.alliance_id)}
            disabled={syncMutation.isPending}
          >
            Sync
          </Button>
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Alliances</h1>
          <p className="text-gray-400">Alliance tracking and management</p>
        </div>
      </div>

      {/* Alliance Statistics */}
      {selectedAlliance && statistics && (
        <Card title={`${selectedAlliance.alliance_name} Statistics`}>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-4">
            <div>
              <div className="text-sm text-gray-400">Total Members</div>
              <div className="text-2xl font-bold text-white">
                {statistics.total_members.toLocaleString()}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Corporations</div>
              <div className="text-2xl font-bold text-white">
                {statistics.total_corporations.toLocaleString()}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Active Wars</div>
              <div className="text-2xl font-bold text-red-400">
                {statistics.active_wars}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Kills (7d)</div>
              <div className="text-2xl font-bold text-green-400">
                {statistics.total_kills_last_week.toLocaleString()}
              </div>
            </div>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setSelectedAlliance(null)}
          >
            Close Details
          </Button>
        </Card>
      )}

      {/* Alliances Table */}
      <Card title="All Alliances">
        {isLoading ? (
          <TableSkeleton rows={10} columns={6} />
        ) : error ? (
          <div className="text-center py-8 text-red-400">
            Error loading alliances
          </div>
        ) : (
          <Table
            data={alliances || []}
            columns={columns}
            keyExtractor={(item) => item.id.toString()}
            emptyMessage="No alliances found"
            defaultSort={{ key: 'members', direction: 'desc' }}
          />
        )}
      </Card>
    </div>
  )
}
