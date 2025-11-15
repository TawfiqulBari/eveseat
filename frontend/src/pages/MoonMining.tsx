import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Table } from '../components/common/Table'
import { Button } from '../components/common/Button'
import { Badge } from '../components/common/Badge'
import { TableSkeleton } from '../components/common/Skeleton'
import { useToast } from '../components/common/Toast'
import { useCharacter } from '../hooks/useCharacter'
import { moonsService, MoonExtraction, MiningLedger } from '../services/moons'
import { logger } from '../utils/logger'
import { formatDistanceToNow, format } from 'date-fns'

export default function MoonMining() {
  const { characterId } = useCharacter()
  const queryClient = useQueryClient()
  const { showToast } = useToast()

  const [activeTab, setActiveTab] = useState<'extractions' | 'ledger'>('extractions')
  const [corporationId] = useState(1) // Default corporation

  const { data: extractions, isLoading: extractionsLoading, error: extractionsError } = useQuery({
    queryKey: ['moon-extractions', corporationId],
    queryFn: () => moonsService.listExtractions({ corporation_id: corporationId }),
    enabled: !!characterId && activeTab === 'extractions',
  })

  const { data: extractionStats, isLoading: extractionStatsLoading } = useQuery({
    queryKey: ['moon-extraction-statistics', corporationId],
    queryFn: () => moonsService.getExtractionStatistics(corporationId),
    enabled: !!characterId,
  })

  const { data: ledger, isLoading: ledgerLoading, error: ledgerError } = useQuery({
    queryKey: ['mining-ledger', corporationId],
    queryFn: () => moonsService.listLedger({ corporation_id: corporationId }),
    enabled: !!characterId && activeTab === 'ledger',
  })

  const { data: ledgerStats, isLoading: ledgerStatsLoading } = useQuery({
    queryKey: ['mining-statistics', corporationId],
    queryFn: () => moonsService.getLedgerStatistics(corporationId, 30),
    enabled: !!characterId,
  })

  const extractionSyncMutation = useMutation({
    mutationFn: () => moonsService.triggerExtractionSync(corporationId),
    onSuccess: () => {
      showToast('Moon extraction sync started', 'success')
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['moon-extractions'] })
        queryClient.invalidateQueries({ queryKey: ['moon-extraction-statistics'] })
      }, 2000)
    },
    onError: (error) => {
      logger.error('Failed to sync extractions', error)
      showToast('Failed to sync extractions', 'error')
    },
  })

  const ledgerSyncMutation = useMutation({
    mutationFn: () => moonsService.triggerLedgerSync(corporationId),
    onSuccess: () => {
      showToast('Mining ledger sync started', 'success')
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['mining-ledger'] })
        queryClient.invalidateQueries({ queryKey: ['mining-statistics'] })
      }, 2000)
    },
    onError: (error) => {
      logger.error('Failed to sync ledger', error)
      showToast('Failed to sync ledger', 'error')
    },
  })

  const getStatusBadge = (status: string | null) => {
    const variants: Record<string, 'success' | 'warning' | 'info' | 'danger' | 'secondary'> = {
      started: 'info',
      ready: 'success',
      collected: 'secondary',
      cancelled: 'danger',
    }
    return <Badge variant={variants[status || ''] || 'secondary'}>{status || 'Unknown'}</Badge>
  }

  const extractionColumns = [
    {
      key: 'moon',
      header: 'Moon',
      sortable: true,
      sortKey: (extraction: MoonExtraction) => extraction.moon_id,
      render: (extraction: MoonExtraction) => (
        <span className="text-white">Moon {extraction.moon_id}</span>
      ),
    },
    {
      key: 'structure',
      header: 'Structure',
      sortable: true,
      sortKey: (extraction: MoonExtraction) => extraction.structure_id,
      render: (extraction: MoonExtraction) => (
        <span className="text-gray-300">Structure {extraction.structure_id}</span>
      ),
    },
    {
      key: 'arrival',
      header: 'Chunk Arrival',
      sortable: true,
      sortKey: (extraction: MoonExtraction) => new Date(extraction.chunk_arrival_time),
      render: (extraction: MoonExtraction) => (
        <div>
          <div className="text-white text-sm">
            {format(new Date(extraction.chunk_arrival_time), 'MMM dd, HH:mm')}
          </div>
          <div className="text-xs text-gray-400">
            {formatDistanceToNow(new Date(extraction.chunk_arrival_time), { addSuffix: true })}
          </div>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      sortKey: (extraction: MoonExtraction) => extraction.status || '',
      render: (extraction: MoonExtraction) => getStatusBadge(extraction.status),
    },
  ]

  const ledgerColumns = [
    {
      key: 'date',
      header: 'Date',
      sortable: true,
      sortKey: (entry: MiningLedger) => new Date(entry.date),
      render: (entry: MiningLedger) => (
        <div className="text-white text-sm">
          {format(new Date(entry.date), 'MMM dd, yyyy')}
        </div>
      ),
    },
    {
      key: 'character',
      header: 'Character',
      sortable: true,
      sortKey: (entry: MiningLedger) => entry.character_id,
      render: (entry: MiningLedger) => (
        <span className="text-white">Character {entry.character_id}</span>
      ),
    },
    {
      key: 'ore',
      header: 'Ore Type',
      sortable: true,
      sortKey: (entry: MiningLedger) => entry.type_id,
      render: (entry: MiningLedger) => (
        <span className="text-gray-300">Type {entry.type_id}</span>
      ),
    },
    {
      key: 'quantity',
      header: 'Quantity',
      sortable: true,
      sortKey: (entry: MiningLedger) => entry.quantity,
      render: (entry: MiningLedger) => (
        <span className="text-green-400">{entry.quantity.toLocaleString()}</span>
      ),
    },
    {
      key: 'system',
      header: 'System',
      sortable: true,
      sortKey: (entry: MiningLedger) => entry.system_id,
      render: (entry: MiningLedger) => (
        <span className="text-gray-300">System {entry.system_id}</span>
      ),
    },
  ]

  if (!characterId) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Moon Mining</h1>
          <p className="text-gray-400">Please select a character</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Moon Mining</h1>
          <p className="text-gray-400">Track moon extractions and mining activity</p>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={() => extractionSyncMutation.mutate()}
            disabled={extractionSyncMutation.isPending}
            variant="secondary"
          >
            {extractionSyncMutation.isPending ? 'Syncing...' : 'Sync Extractions'}
          </Button>
          <Button
            onClick={() => ledgerSyncMutation.mutate()}
            disabled={ledgerSyncMutation.isPending}
          >
            {ledgerSyncMutation.isPending ? 'Syncing...' : 'Sync Ledger'}
          </Button>
        </div>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
        {extractionStatsLoading ? (
          <Card title="Loading..."><div className="text-gray-400">...</div></Card>
        ) : extractionStats ? (
          <>
            <Card title="Total Extractions">
              <div className="text-3xl font-bold text-white">{extractionStats.total_extractions}</div>
            </Card>
            <Card title="Active">
              <div className="text-3xl font-bold text-blue-400">{extractionStats.active_extractions}</div>
            </Card>
            <Card title="Ready">
              <div className="text-3xl font-bold text-green-400">{extractionStats.ready_extractions}</div>
            </Card>
            <Card title="Upcoming (24h)">
              <div className="text-3xl font-bold text-yellow-400">{extractionStats.upcoming_arrivals}</div>
            </Card>
          </>
        ) : null}

        {ledgerStatsLoading ? (
          <Card title="Loading..."><div className="text-gray-400">...</div></Card>
        ) : ledgerStats ? (
          <Card title="Total Miners (30d)">
            <div className="text-3xl font-bold text-purple-400">{ledgerStats.total_miners}</div>
          </Card>
        ) : null}
      </div>

      {/* Tabs */}
      <Card>
        <div className="flex gap-4 border-b border-eve-gray pb-4">
          <button
            onClick={() => setActiveTab('extractions')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'extractions'
                ? 'bg-eve-blue text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Extractions
          </button>
          <button
            onClick={() => setActiveTab('ledger')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'ledger'
                ? 'bg-eve-blue text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Mining Ledger
          </button>
        </div>

        {/* Extractions Tab */}
        {activeTab === 'extractions' && (
          <div className="mt-6">
            {extractionsLoading ? (
              <TableSkeleton rows={10} columns={4} />
            ) : extractionsError ? (
              <div className="text-center py-8 text-red-400">
                Error loading extractions. Try syncing.
              </div>
            ) : (
              <Table
                data={extractions || []}
                columns={extractionColumns}
                keyExtractor={(item) => item.id.toString()}
                emptyMessage="No extractions found. Click 'Sync Extractions' to fetch from EVE Online."
                defaultSort={{ key: 'arrival', direction: 'asc' }}
              />
            )}
          </div>
        )}

        {/* Ledger Tab */}
        {activeTab === 'ledger' && (
          <div className="mt-6">
            {ledgerLoading ? (
              <TableSkeleton rows={10} columns={5} />
            ) : ledgerError ? (
              <div className="text-center py-8 text-red-400">
                Error loading ledger. Try syncing.
              </div>
            ) : (
              <Table
                data={ledger || []}
                columns={ledgerColumns}
                keyExtractor={(item) => item.id.toString()}
                emptyMessage="No ledger entries found. Click 'Sync Ledger' to fetch from EVE Online."
                defaultSort={{ key: 'date', direction: 'desc' }}
              />
            )}
          </div>
        )}
      </Card>
    </div>
  )
}
