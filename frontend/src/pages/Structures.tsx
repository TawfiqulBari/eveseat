import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Table } from '../components/common/Table'
import { Button } from '../components/common/Button'
import { Badge } from '../components/common/Badge'
import { TableSkeleton } from '../components/common/Skeleton'
import { useToast } from '../components/common/Toast'
import { useCharacter } from '../hooks/useCharacter'
import { structuresService, Structure } from '../services/structures'
import { logger } from '../utils/logger'
import { formatDistanceToNow, format } from 'date-fns'

export default function Structures() {
  const { characterId } = useCharacter()
  const queryClient = useQueryClient()
  const { showToast } = useToast()

  const [filters, setFilters] = useState({
    skip: 0,
    limit: 50,
    corporation_id: 1, // Default corporation
    system_id: undefined as number | undefined,
    state: undefined as string | undefined,
  })

  const { data: structures, isLoading, error } = useQuery({
    queryKey: ['structures', filters],
    queryFn: () => structuresService.listStructures({
      ...filters,
      offset: filters.skip,
    }),
    enabled: !!characterId,
  })

  const { data: statistics, isLoading: statsLoading } = useQuery({
    queryKey: ['structure-statistics', filters.corporation_id],
    queryFn: () => structuresService.getStatistics(filters.corporation_id),
    enabled: !!filters.corporation_id,
  })

  const syncMutation = useMutation({
    mutationFn: () => structuresService.triggerSync(filters.corporation_id),
    onSuccess: () => {
      showToast('Structures sync started', 'success')
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['structures'] })
        queryClient.invalidateQueries({ queryKey: ['structure-statistics'] })
      }, 2000)
    },
    onError: (error) => {
      logger.error('Failed to sync structures', error)
      showToast('Failed to sync structures', 'error')
    },
  })

  const getStateBadge = (state: string | null) => {
    const variants: Record<string, 'success' | 'warning' | 'info' | 'danger' | 'secondary'> = {
      online: 'success',
      offline: 'secondary',
      anchoring: 'info',
      unanchoring: 'warning',
      vulnerable: 'danger',
    }
    return <Badge variant={variants[state || ''] || 'secondary'}>{state || 'Unknown'}</Badge>
  }

  const columns = [
    {
      key: 'name',
      header: 'Name',
      sortable: true,
      sortKey: (structure: Structure) => structure.name || '',
      render: (structure: Structure) => (
        <div>
          <div className="text-white font-medium">{structure.name || `Structure ${structure.structure_id}`}</div>
          <div className="text-xs text-gray-400">Type {structure.type_id}</div>
        </div>
      ),
    },
    {
      key: 'system',
      header: 'System',
      sortable: true,
      sortKey: (structure: Structure) => structure.system_id,
      render: (structure: Structure) => (
        <span className="text-gray-300">System {structure.system_id}</span>
      ),
    },
    {
      key: 'state',
      header: 'State',
      sortable: true,
      sortKey: (structure: Structure) => structure.state || '',
      render: (structure: Structure) => getStateBadge(structure.state),
    },
    {
      key: 'fuel',
      header: 'Fuel Expires',
      sortable: true,
      sortKey: (structure: Structure) => structure.fuel_expires ? new Date(structure.fuel_expires) : new Date(0),
      render: (structure: Structure) => (
        structure.fuel_expires ? (
          <div>
            <div className="text-white text-sm">
              {format(new Date(structure.fuel_expires), 'MMM dd, yyyy')}
            </div>
            <div className="text-xs text-gray-400">
              {formatDistanceToNow(new Date(structure.fuel_expires), { addSuffix: true })}
            </div>
          </div>
        ) : (
          <span className="text-gray-500">-</span>
        )
      ),
    },
    {
      key: 'reinforce',
      header: 'Reinforce',
      sortable: false,
      render: (structure: Structure) => (
        structure.next_reinforce_hour !== null ? (
          <span className="text-gray-300">
            {structure.next_reinforce_hour}:00 {structure.next_reinforce_day !== null ? `(Day ${structure.next_reinforce_day})` : ''}
          </span>
        ) : (
          <span className="text-gray-500">-</span>
        )
      ),
    },
  ]

  if (!characterId) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Structures</h1>
          <p className="text-gray-400">Please select a character</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Corporation Structures</h1>
          <p className="text-gray-400">Manage your corporation's structures</p>
        </div>
        <Button
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
        >
          {syncMutation.isPending ? 'Syncing...' : 'Sync Structures'}
        </Button>
      </div>

      {/* Statistics */}
      {statsLoading ? (
        <Card title="Structure Statistics">
          <div className="text-gray-400">Loading statistics...</div>
        </Card>
      ) : statistics ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card title="Total Structures">
            <div className="text-3xl font-bold text-white">{statistics.total_structures}</div>
          </Card>
          <Card title="Online">
            <div className="text-3xl font-bold text-green-400">{statistics.online_structures}</div>
          </Card>
          <Card title="Low Fuel (< 7d)">
            <div className="text-3xl font-bold text-red-400">{statistics.low_fuel_structures}</div>
          </Card>
        </div>
      ) : null}

      {/* Filters */}
      <Card title="Filters">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              System ID
            </label>
            <input
              type="number"
              value={filters.system_id || ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  system_id: e.target.value ? parseInt(e.target.value) : undefined,
                })
              }
              className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
              placeholder="Filter by system..."
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              State
            </label>
            <select
              value={filters.state || ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  state: e.target.value || undefined,
                })
              }
              className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
            >
              <option value="">All States</option>
              <option value="online">Online</option>
              <option value="offline">Offline</option>
              <option value="anchoring">Anchoring</option>
              <option value="unanchoring">Unanchoring</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Structures Table */}
      <Card title={`Structures (${structures?.length || 0})`}>
        {isLoading ? (
          <TableSkeleton rows={10} columns={5} />
        ) : error ? (
          <div className="text-center py-8 text-red-400">
            Error loading structures. Try syncing your structures.
          </div>
        ) : (
          <Table
            data={structures || []}
            columns={columns}
            keyExtractor={(item) => item.id.toString()}
            emptyMessage="No structures found. Click 'Sync Structures' to fetch from EVE Online."
            defaultSort={{ key: 'name', direction: 'asc' }}
          />
        )}
      </Card>
    </div>
  )
}
