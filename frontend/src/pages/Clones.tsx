import React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Table } from '../components/common/Table'
import { Button } from '../components/common/Button'
import { Badge } from '../components/common/Badge'
import { TableSkeleton } from '../components/common/Skeleton'
import { useToast } from '../components/common/Toast'
import { useCharacter } from '../hooks/useCharacter'
import { clonesService, Clone, ActiveImplant } from '../services/clones'
import { logger } from '../utils/logger'

export default function Clones() {
  const { characterId } = useCharacter()
  const queryClient = useQueryClient()
  const { showToast } = useToast()

  const { data: clones, isLoading: clonesLoading, error: clonesError } = useQuery({
    queryKey: ['clones', characterId],
    queryFn: () => clonesService.listClones({
      character_id: characterId || undefined,
    }),
    enabled: !!characterId,
  })

  const { data: activeImplants, isLoading: implantsLoading } = useQuery({
    queryKey: ['active-implants', characterId],
    queryFn: () => clonesService.getActiveImplants(characterId!),
    enabled: !!characterId,
  })

  const { data: statistics, isLoading: statsLoading } = useQuery({
    queryKey: ['clone-statistics', characterId],
    queryFn: () => clonesService.getStatistics(characterId!),
    enabled: !!characterId,
  })

  const syncMutation = useMutation({
    mutationFn: () => clonesService.triggerSync(characterId!),
    onSuccess: () => {
      showToast('Clones sync started', 'success')
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['clones'] })
        queryClient.invalidateQueries({ queryKey: ['active-implants'] })
        queryClient.invalidateQueries({ queryKey: ['clone-statistics'] })
      }, 2000)
    },
    onError: (error) => {
      logger.error('Failed to sync clones', error)
      showToast('Failed to sync clones', 'error')
    },
  })

  const cloneColumns = [
    {
      key: 'name',
      header: 'Clone Name',
      sortable: true,
      sortKey: (clone: Clone) => clone.name || `Clone ${clone.jump_clone_id}`,
      render: (clone: Clone) => (
        <span className="text-white font-medium">
          {clone.name || `Clone ${clone.jump_clone_id}`}
        </span>
      ),
    },
    {
      key: 'location',
      header: 'Location',
      sortable: true,
      sortKey: (clone: Clone) => clone.location_id,
      render: (clone: Clone) => (
        <div>
          <div className="text-white text-sm">Location {clone.location_id}</div>
          {clone.location_type && (
            <div className="text-xs text-gray-400">{clone.location_type}</div>
          )}
        </div>
      ),
    },
    {
      key: 'implants',
      header: 'Implants',
      sortable: true,
      sortKey: (clone: Clone) => clone.implants.length,
      render: (clone: Clone) => (
        <Badge variant={clone.implants.length > 0 ? 'success' : 'secondary'}>
          {clone.implants.length} implants
        </Badge>
      ),
    },
    {
      key: 'implant_list',
      header: 'Implant Types',
      sortable: false,
      render: (clone: Clone) => (
        clone.implants.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {clone.implants.slice(0, 5).map((typeId, idx) => (
              <span key={idx} className="text-xs text-gray-400">
                {typeId}{idx < Math.min(4, clone.implants.length - 1) ? ',' : ''}
              </span>
            ))}
            {clone.implants.length > 5 && (
              <span className="text-xs text-gray-400">+{clone.implants.length - 5} more</span>
            )}
          </div>
        ) : (
          <span className="text-gray-500 text-sm">No implants</span>
        )
      ),
    },
  ]

  const implantColumns = [
    {
      key: 'type_id',
      header: 'Type',
      sortable: true,
      sortKey: (implant: ActiveImplant) => implant.type_id,
      render: (implant: ActiveImplant) => (
        <span className="text-white">Type {implant.type_id}</span>
      ),
    },
    {
      key: 'name',
      header: 'Name',
      sortable: true,
      sortKey: (implant: ActiveImplant) => implant.name || '',
      render: (implant: ActiveImplant) => (
        <span className="text-gray-300">
          {implant.name || 'Unknown Implant'}
        </span>
      ),
    },
    {
      key: 'slot',
      header: 'Slot',
      sortable: true,
      sortKey: (implant: ActiveImplant) => implant.slot || 0,
      render: (implant: ActiveImplant) => (
        implant.slot !== null ? (
          <Badge variant="info">Slot {implant.slot}</Badge>
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
          <h1 className="text-3xl font-bold text-white mb-2">Jump Clones</h1>
          <p className="text-gray-400">Please select a character</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Jump Clones</h1>
          <p className="text-gray-400">Manage your jump clones and implants</p>
        </div>
        <Button
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
        >
          {syncMutation.isPending ? 'Syncing...' : 'Sync Clones'}
        </Button>
      </div>

      {/* Statistics */}
      {statsLoading ? (
        <Card title="Clone Statistics">
          <div className="text-gray-400">Loading statistics...</div>
        </Card>
      ) : statistics ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Card title="Total Clones">
            <div className="text-3xl font-bold text-white">{statistics.total_jump_clones}</div>
          </Card>
          <Card title="Clones with Implants">
            <div className="text-3xl font-bold text-green-400">{statistics.clones_with_implants}</div>
          </Card>
          <Card title="Active Implants">
            <div className="text-3xl font-bold text-blue-400">{statistics.active_implants}</div>
          </Card>
          <Card title="Total Value">
            <div className="text-2xl font-bold text-yellow-400">
              {statistics.total_implant_value !== null
                ? `${(statistics.total_implant_value / 1000000).toFixed(1)}M ISK`
                : 'N/A'}
            </div>
          </Card>
        </div>
      ) : null}

      {/* Active Implants */}
      <Card title="Active Implants">
        {implantsLoading ? (
          <div className="text-gray-400">Loading active implants...</div>
        ) : activeImplants && activeImplants.length > 0 ? (
          <Table
            data={activeImplants}
            columns={implantColumns}
            keyExtractor={(item) => item.id.toString()}
            emptyMessage="No active implants"
            defaultSort={{ key: 'slot', direction: 'asc' }}
          />
        ) : (
          <div className="text-center py-4 text-gray-400">
            No active implants in your current clone
          </div>
        )}
      </Card>

      {/* Jump Clones Table */}
      <Card title={`Jump Clones (${clones?.length || 0})`}>
        {clonesLoading ? (
          <TableSkeleton rows={10} columns={4} />
        ) : clonesError ? (
          <div className="text-center py-8 text-red-400">
            Error loading jump clones. Try syncing your clones.
          </div>
        ) : (
          <Table
            data={clones || []}
            columns={cloneColumns}
            keyExtractor={(item) => item.id.toString()}
            emptyMessage="No jump clones found. Click 'Sync Clones' to fetch from EVE Online."
            defaultSort={{ key: 'name', direction: 'asc' }}
          />
        )}
      </Card>
    </div>
  )
}
