import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Table } from '../components/common/Table'
import { Button } from '../components/common/Button'
import { Badge } from '../components/common/Badge'
import { TableSkeleton } from '../components/common/Skeleton'
import { useToast } from '../components/common/Toast'
import { useCharacter } from '../hooks/useCharacter'
import { blueprintsService, Blueprint } from '../services/blueprints'
import { logger } from '../utils/logger'

export default function Blueprints() {
  const { characterId } = useCharacter()
  const queryClient = useQueryClient()
  const { showToast } = useToast()

  const [filters, setFilters] = useState({
    skip: 0,
    limit: 50,
    location_id: undefined as number | undefined,
    is_original: undefined as boolean | undefined,
  })

  const { data: blueprints, isLoading: blueprintsLoading, error: blueprintsError } = useQuery({
    queryKey: ['blueprints', characterId, filters],
    queryFn: () => blueprintsService.listBlueprints({
      character_id: characterId || undefined,
      ...filters,
      offset: filters.skip,
    }),
    enabled: !!characterId,
  })

  const { data: statistics, isLoading: statsLoading } = useQuery({
    queryKey: ['blueprint-statistics', characterId],
    queryFn: () => blueprintsService.getStatistics(characterId!),
    enabled: !!characterId,
  })

  const syncMutation = useMutation({
    mutationFn: () => blueprintsService.triggerSync(characterId!),
    onSuccess: () => {
      showToast('Blueprints sync started', 'success')
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['blueprints'] })
        queryClient.invalidateQueries({ queryKey: ['blueprint-statistics'] })
      }, 2000)
    },
    onError: (error) => {
      logger.error('Failed to sync blueprints', error)
      showToast('Failed to sync blueprints', 'error')
    },
  })

  const getBlueprintType = (runs: number) => {
    return runs === -1 ? 'BPO' : 'BPC'
  }

  const getResearchLevel = (me: number, te: number) => {
    if (me === 10 && te === 20) {
      return <Badge variant="success">Fully Researched</Badge>
    }
    if (me > 0 || te > 0) {
      return <Badge variant="warning">Partially Researched</Badge>
    }
    return <Badge variant="secondary">Unresearched</Badge>
  }

  const columns = [
    {
      key: 'type_id',
      header: 'Blueprint',
      sortable: true,
      sortKey: (bp: Blueprint) => bp.type_id,
      render: (bp: Blueprint) => (
        <span className="text-white">Type {bp.type_id}</span>
      ),
    },
    {
      key: 'blueprint_type',
      header: 'Type',
      sortable: true,
      sortKey: (bp: Blueprint) => bp.runs,
      render: (bp: Blueprint) => (
        <Badge variant={bp.runs === -1 ? 'info' : 'secondary'}>
          {getBlueprintType(bp.runs)}
        </Badge>
      ),
    },
    {
      key: 'me',
      header: 'ME',
      sortable: true,
      sortKey: (bp: Blueprint) => bp.material_efficiency,
      render: (bp: Blueprint) => (
        <span className={bp.material_efficiency === 10 ? 'text-green-400 font-medium' : 'text-gray-300'}>
          {bp.material_efficiency}
        </span>
      ),
    },
    {
      key: 'te',
      header: 'TE',
      sortable: true,
      sortKey: (bp: Blueprint) => bp.time_efficiency,
      render: (bp: Blueprint) => (
        <span className={bp.time_efficiency === 20 ? 'text-green-400 font-medium' : 'text-gray-300'}>
          {bp.time_efficiency}
        </span>
      ),
    },
    {
      key: 'research',
      header: 'Research Status',
      sortable: false,
      render: (bp: Blueprint) => getResearchLevel(bp.material_efficiency, bp.time_efficiency),
    },
    {
      key: 'runs',
      header: 'Runs',
      sortable: true,
      sortKey: (bp: Blueprint) => bp.runs,
      render: (bp: Blueprint) => (
        <span className="text-gray-300">
          {bp.runs === -1 ? 'Original' : bp.runs}
        </span>
      ),
    },
    {
      key: 'quantity',
      header: 'Quantity',
      sortable: true,
      sortKey: (bp: Blueprint) => bp.quantity,
      render: (bp: Blueprint) => (
        <span className="text-gray-300">{bp.quantity}</span>
      ),
    },
    {
      key: 'location',
      header: 'Location',
      sortable: true,
      sortKey: (bp: Blueprint) => bp.location_id,
      render: (bp: Blueprint) => (
        <div>
          <div className="text-white text-sm">Location {bp.location_id}</div>
          <div className="text-xs text-gray-400">{bp.location_flag}</div>
        </div>
      ),
    },
  ]

  if (!characterId) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Blueprints</h1>
          <p className="text-gray-400">Please select a character</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Blueprints</h1>
          <p className="text-gray-400">Manage your blueprints and research</p>
        </div>
        <Button
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
        >
          {syncMutation.isPending ? 'Syncing...' : 'Sync Blueprints'}
        </Button>
      </div>

      {/* Statistics */}
      {statsLoading ? (
        <Card title="Blueprint Statistics">
          <div className="text-gray-400">Loading statistics...</div>
        </Card>
      ) : statistics ? (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
          <Card title="Total Blueprints">
            <div className="text-3xl font-bold text-white">{statistics.total_blueprints}</div>
          </Card>
          <Card title="BPOs">
            <div className="text-3xl font-bold text-blue-400">{statistics.bpos}</div>
          </Card>
          <Card title="BPCs">
            <div className="text-3xl font-bold text-purple-400">{statistics.bpcs}</div>
          </Card>
          <Card title="Avg ME">
            <div className="text-3xl font-bold text-green-400">{statistics.avg_me}</div>
          </Card>
          <Card title="Avg TE">
            <div className="text-3xl font-bold text-yellow-400">{statistics.avg_te}</div>
          </Card>
        </div>
      ) : null}

      {/* Research Progress */}
      {statistics && (
        <Card title="Research Progress">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="text-4xl font-bold text-green-400">{statistics.fully_researched}</div>
              <div className="text-sm text-gray-400 mt-1">Fully Researched (ME 10 / TE 20)</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-yellow-400">
                {statistics.total_blueprints - statistics.fully_researched}
              </div>
              <div className="text-sm text-gray-400 mt-1">Need Research</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-white">
                {statistics.total_blueprints > 0
                  ? Math.round((statistics.fully_researched / statistics.total_blueprints) * 100)
                  : 0}%
              </div>
              <div className="text-sm text-gray-400 mt-1">Research Completion</div>
            </div>
          </div>
        </Card>
      )}

      {/* Filters */}
      <Card title="Filters">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Blueprint Type
            </label>
            <select
              value={filters.is_original === undefined ? '' : filters.is_original ? 'bpo' : 'bpc'}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  is_original: e.target.value === '' ? undefined : e.target.value === 'bpo',
                })
              }
              className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
            >
              <option value="">All Types</option>
              <option value="bpo">Blueprint Originals (BPO)</option>
              <option value="bpc">Blueprint Copies (BPC)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Location ID
            </label>
            <input
              type="number"
              value={filters.location_id || ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  location_id: e.target.value ? parseInt(e.target.value) : undefined,
                })
              }
              className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
              placeholder="Filter by location"
            />
          </div>
        </div>
      </Card>

      {/* Blueprints Table */}
      <Card title={`Blueprints (${blueprints?.length || 0})`}>
        {blueprintsLoading ? (
          <TableSkeleton rows={10} columns={8} />
        ) : blueprintsError ? (
          <div className="text-center py-8 text-red-400">
            Error loading blueprints. Try syncing your blueprints.
          </div>
        ) : (
          <Table
            data={blueprints || []}
            columns={columns}
            keyExtractor={(item) => item.id.toString()}
            emptyMessage="No blueprints found. Click 'Sync Blueprints' to fetch from EVE Online."
            defaultSort={{ key: 'type_id', direction: 'asc' }}
          />
        )}
      </Card>
    </div>
  )
}
