import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Table } from '../components/common/Table'
import { Button } from '../components/common/Button'
import { TableSkeleton } from '../components/common/Skeleton'
import { useToast } from '../components/common/Toast'
import { warsService, War } from '../services/wars'
import { logger } from '../utils/logger'
import { format } from 'date-fns'

export default function Wars() {
  const queryClient = useQueryClient()
  const { showToast } = useToast()
  const [activeOnly, setActiveOnly] = useState(true)

  const { data: wars, isLoading, error } = useQuery({
    queryKey: ['wars', activeOnly],
    queryFn: () => warsService.listWars(activeOnly),
  })

  const { data: statistics } = useQuery({
    queryKey: ['war-statistics'],
    queryFn: () => warsService.getWarStatistics(),
  })

  const syncMutation = useMutation({
    mutationFn: () => warsService.syncWars(),
    onSuccess: () => {
      showToast('Wars sync started', 'success')
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['wars'] })
        queryClient.invalidateQueries({ queryKey: ['war-statistics'] })
      }, 3000)
    },
    onError: (error) => {
      logger.error('Failed to sync wars', error)
      showToast('Failed to sync wars', 'error')
    },
  })

  const formatISK = (amount: number) => {
    if (amount >= 1e9) return `${(amount / 1e9).toFixed(2)}B ISK`
    if (amount >= 1e6) return `${(amount / 1e6).toFixed(2)}M ISK`
    if (amount >= 1e3) return `${(amount / 1e3).toFixed(2)}K ISK`
    return `${amount.toLocaleString()} ISK`
  }

  const columns = [
    {
      key: 'war_id',
      header: 'War ID',
      sortable: true,
      sortKey: (war: War) => war.war_id,
      render: (war: War) => (
        <span className="text-white font-mono">#{war.war_id}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      sortKey: (war: War) => war.is_active,
      render: (war: War) => (
        <span
          className={`px-2 py-1 rounded text-xs font-medium ${
            war.is_active
              ? 'bg-red-900 text-red-200'
              : 'bg-gray-700 text-gray-300'
          }`}
        >
          {war.is_active ? 'Active' : 'Finished'}
        </span>
      ),
    },
    {
      key: 'type',
      header: 'Type',
      sortable: true,
      sortKey: (war: War) => war.is_mutual,
      render: (war: War) => (
        <span className="text-gray-300">
          {war.is_mutual ? 'Mutual' : 'Aggression'}
          {war.is_open_for_allies && ' (Allies)'}
        </span>
      ),
    },
    {
      key: 'declared',
      header: 'Declared',
      sortable: true,
      sortKey: (war: War) => (war.declared ? new Date(war.declared) : null),
      render: (war: War) => (
        <span className="text-gray-300">
          {war.declared
            ? format(new Date(war.declared), 'MMM dd, yyyy')
            : 'Unknown'}
        </span>
      ),
    },
    {
      key: 'aggressor_kills',
      header: 'Aggressor Kills',
      sortable: true,
      sortKey: (war: War) => war.aggressor_ships_killed,
      render: (war: War) => (
        <div className="text-sm">
          <div className="text-white">{war.aggressor_ships_killed} ships</div>
          <div className="text-green-400">{formatISK(war.aggressor_isk_destroyed)}</div>
        </div>
      ),
    },
    {
      key: 'defender_kills',
      header: 'Defender Kills',
      sortable: true,
      sortKey: (war: War) => war.defender_ships_killed,
      render: (war: War) => (
        <div className="text-sm">
          <div className="text-white">{war.defender_ships_killed} ships</div>
          <div className="text-green-400">{formatISK(war.defender_isk_destroyed)}</div>
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Wars</h1>
          <p className="text-gray-400">Track alliance and corporation wars</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant={activeOnly ? 'primary' : 'secondary'}
            onClick={() => setActiveOnly(!activeOnly)}
          >
            {activeOnly ? 'Active Only' : 'All Wars'}
          </Button>
          <Button
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
          >
            {syncMutation.isPending ? 'Syncing...' : 'Sync Wars'}
          </Button>
        </div>
      </div>

      {/* War Statistics */}
      {statistics && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Card title="Total Wars">
            <div className="text-3xl font-bold text-white">
              {statistics.total_wars}
            </div>
          </Card>

          <Card title="Active Wars">
            <div className="text-3xl font-bold text-red-400">
              {statistics.active_wars}
            </div>
          </Card>

          <Card title="Total Kills">
            <div className="text-3xl font-bold text-green-400">
              {statistics.total_kills.toLocaleString()}
            </div>
          </Card>

          <Card title="ISK Destroyed">
            <div className="text-2xl font-bold text-orange-400">
              {formatISK(statistics.total_isk_destroyed)}
            </div>
          </Card>
        </div>
      )}

      {/* Wars Table */}
      <Card title={`${activeOnly ? 'Active' : 'All'} Wars`}>
        {isLoading ? (
          <TableSkeleton rows={10} columns={6} />
        ) : error ? (
          <div className="text-center py-8 text-red-400">
            Error loading wars. Try syncing wars first.
          </div>
        ) : (
          <Table
            data={wars || []}
            columns={columns}
            keyExtractor={(item) => item.id.toString()}
            emptyMessage="No wars found. Click 'Sync Wars' to fetch data."
            defaultSort={{ key: 'declared', direction: 'desc' }}
          />
        )}
      </Card>
    </div>
  )
}
