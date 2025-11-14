import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Table } from '../components/common/Table'
import { Button } from '../components/common/Button'
import { Badge } from '../components/common/Badge'
import { TableSkeleton } from '../components/common/Skeleton'
import { useToast } from '../components/common/Toast'
import { useCharacter } from '../hooks/useCharacter'
import { fittingsService, Fitting } from '../services/fittings'
import { logger } from '../utils/logger'

export default function Fittings() {
  const { characterId } = useCharacter()
  const queryClient = useQueryClient()
  const { showToast } = useToast()

  const [filters, setFilters] = useState({
    skip: 0,
    limit: 50,
    ship_type_id: undefined as number | undefined,
  })

  const [selectedFitting, setSelectedFitting] = useState<Fitting | null>(null)

  const { data: fittings, isLoading: fittingsLoading, error: fittingsError } = useQuery({
    queryKey: ['fittings', characterId, filters],
    queryFn: () => fittingsService.listFittings({
      character_id: characterId || undefined,
      ...filters,
      offset: filters.skip,
    }),
    enabled: !!characterId,
  })

  const syncMutation = useMutation({
    mutationFn: () => fittingsService.triggerSync(characterId!),
    onSuccess: () => {
      showToast('Fittings sync started', 'success')
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['fittings'] })
      }, 2000)
    },
    onError: (error) => {
      logger.error('Failed to sync fittings', error)
      showToast('Failed to sync fittings', 'error')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (fittingId: number) => fittingsService.deleteFitting(fittingId),
    onSuccess: () => {
      showToast('Fitting deleted successfully', 'success')
      queryClient.invalidateQueries({ queryKey: ['fittings'] })
      setSelectedFitting(null)
    },
    onError: (error) => {
      logger.error('Failed to delete fitting', error)
      showToast('Failed to delete fitting', 'error')
    },
  })

  const columns = [
    {
      key: 'name',
      header: 'Fitting Name',
      sortable: true,
      sortKey: (fitting: Fitting) => fitting.name,
      render: (fitting: Fitting) => (
        <div>
          <div className="text-white font-medium">{fitting.name}</div>
          {fitting.description && (
            <div className="text-xs text-gray-400 mt-1">{fitting.description}</div>
          )}
        </div>
      ),
    },
    {
      key: 'ship_type_id',
      header: 'Ship Type',
      sortable: true,
      sortKey: (fitting: Fitting) => fitting.ship_type_id,
      render: (fitting: Fitting) => (
        <Badge variant="info">Type {fitting.ship_type_id}</Badge>
      ),
    },
    {
      key: 'items',
      header: 'Modules',
      sortable: true,
      sortKey: (fitting: Fitting) => fitting.items.length,
      render: (fitting: Fitting) => (
        <span className="text-gray-300">{fitting.items.length} items</span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      sortable: false,
      render: (fitting: Fitting) => (
        <div className="flex gap-2">
          <Button
            onClick={() => setSelectedFitting(fitting)}
            variant="secondary"
            size="sm"
          >
            View Details
          </Button>
          <Button
            onClick={() => deleteMutation.mutate(fitting.id)}
            variant="danger"
            size="sm"
            disabled={deleteMutation.isPending}
          >
            Delete
          </Button>
        </div>
      ),
    },
  ]

  if (!characterId) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Ship Fittings</h1>
          <p className="text-gray-400">Please select a character</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Ship Fittings</h1>
          <p className="text-gray-400">Manage your saved ship fittings</p>
        </div>
        <Button
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
        >
          {syncMutation.isPending ? 'Syncing...' : 'Sync Fittings'}
        </Button>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card title="Total Fittings">
          <div className="text-3xl font-bold text-white">{fittings?.length || 0}</div>
        </Card>
        <Card title="Unique Ships">
          <div className="text-3xl font-bold text-blue-400">
            {new Set(fittings?.map(f => f.ship_type_id) || []).size}
          </div>
        </Card>
        <Card title="Total Modules">
          <div className="text-3xl font-bold text-green-400">
            {fittings?.reduce((sum, f) => sum + f.items.length, 0) || 0}
          </div>
        </Card>
      </div>

      {/* Filters */}
      <Card title="Filters">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Ship Type ID
            </label>
            <input
              type="number"
              value={filters.ship_type_id || ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  ship_type_id: e.target.value ? parseInt(e.target.value) : undefined,
                })
              }
              className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
              placeholder="Filter by ship type..."
            />
          </div>
        </div>
      </Card>

      {/* Fittings Table */}
      <Card title={`Ship Fittings (${fittings?.length || 0})`}>
        {fittingsLoading ? (
          <TableSkeleton rows={10} columns={4} />
        ) : fittingsError ? (
          <div className="text-center py-8 text-red-400">
            Error loading fittings. Try syncing your fittings.
          </div>
        ) : (
          <Table
            data={fittings || []}
            columns={columns}
            keyExtractor={(item) => item.id.toString()}
            emptyMessage="No fittings found. Click 'Sync Fittings' to fetch from EVE Online."
            defaultSort={{ key: 'name', direction: 'asc' }}
          />
        )}
      </Card>

      {/* Fitting Details Modal */}
      {selectedFitting && (
        <Card title={`Fitting Details: ${selectedFitting.name}`}>
          <div className="space-y-4">
            <div>
              <div className="text-sm text-gray-400">Ship Type</div>
              <div className="text-white">Type {selectedFitting.ship_type_id}</div>
            </div>
            {selectedFitting.description && (
              <div>
                <div className="text-sm text-gray-400">Description</div>
                <div className="text-white">{selectedFitting.description}</div>
              </div>
            )}
            <div>
              <div className="text-sm text-gray-400 mb-2">Modules ({selectedFitting.items.length})</div>
              <div className="space-y-2">
                {selectedFitting.items.map((item, idx) => (
                  <div key={idx} className="p-3 bg-eve-darker rounded-lg flex justify-between items-center">
                    <div>
                      <span className="text-white">Type {item.type_id}</span>
                      <span className="text-gray-400 ml-2">({item.flag})</span>
                    </div>
                    <span className="text-gray-300">x{item.quantity}</span>
                  </div>
                ))}
              </div>
            </div>
            <Button
              onClick={() => setSelectedFitting(null)}
              variant="secondary"
              fullWidth
            >
              Close
            </Button>
          </div>
        </Card>
      )}
    </div>
  )
}
