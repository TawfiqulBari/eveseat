import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Table } from '../components/common/Table'
import { Button } from '../components/common/Button'
import { TableSkeleton } from '../components/common/Skeleton'
import { useToast } from '../components/common/Toast'
import { useCharacter } from '../hooks/useCharacter'
import {
  factionWarfareService,
  FactionWarfareSystem,
  FactionWarfareStatistics,
} from '../services/faction_warfare'
import { logger } from '../utils/logger'

export default function FactionWarfare() {
  const { characterId } = useCharacter()
  const queryClient = useQueryClient()
  const { showToast } = useToast()
  const [contestedOnly, setContestedOnly] = useState(false)
  const [activeTab, setActiveTab] = useState<'systems' | 'statistics'>('systems')

  const { data: systems, isLoading: systemsLoading } = useQuery({
    queryKey: ['fw-systems', contestedOnly],
    queryFn: () => factionWarfareService.listSystems(contestedOnly),
  })

  const { data: statistics, isLoading: statsLoading } = useQuery({
    queryKey: ['fw-statistics'],
    queryFn: () => factionWarfareService.getStatistics(),
  })

  const { data: summary } = useQuery({
    queryKey: ['fw-summary'],
    queryFn: () => factionWarfareService.getSummary(),
  })

  const { data: characterStats } = useQuery({
    queryKey: ['fw-character-stats', characterId],
    queryFn: () => factionWarfareService.getCharacterStats(characterId!),
    enabled: !!characterId,
  })

  const syncMutation = useMutation({
    mutationFn: () => factionWarfareService.syncSystems(),
    onSuccess: () => {
      showToast('Faction warfare sync started', 'success')
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['fw-systems'] })
        queryClient.invalidateQueries({ queryKey: ['fw-statistics'] })
        queryClient.invalidateQueries({ queryKey: ['fw-summary'] })
      }, 3000)
    },
    onError: (error) => {
      logger.error('Failed to sync faction warfare', error)
      showToast('Failed to sync faction warfare', 'error')
    },
  })

  const getFactionName = (factionId: number) => {
    const factions: { [key: number]: string } = {
      500001: 'Caldari State',
      500002: 'Minmatar Republic',
      500003: 'Amarr Empire',
      500004: 'Gallente Federation',
    }
    return factions[factionId] || `Faction ${factionId}`
  }

  const getContestedColor = (contested: string) => {
    switch (contested) {
      case 'contested':
        return 'bg-red-900 text-red-200'
      case 'vulnerable':
        return 'bg-yellow-900 text-yellow-200'
      case 'uncontested':
        return 'bg-green-900 text-green-200'
      default:
        return 'bg-gray-700 text-gray-300'
    }
  }

  const systemColumns = [
    {
      key: 'system',
      header: 'Solar System',
      sortable: true,
      sortKey: (system: FactionWarfareSystem) => system.solar_system_id,
      render: (system: FactionWarfareSystem) => (
        <span className="text-white font-mono">{system.solar_system_id}</span>
      ),
    },
    {
      key: 'occupier',
      header: 'Occupier',
      sortable: true,
      sortKey: (system: FactionWarfareSystem) => system.occupier_faction_id,
      render: (system: FactionWarfareSystem) => (
        <span className="text-gray-300">
          {getFactionName(system.occupier_faction_id)}
        </span>
      ),
    },
    {
      key: 'owner',
      header: 'Owner',
      sortable: true,
      sortKey: (system: FactionWarfareSystem) => system.owner_faction_id,
      render: (system: FactionWarfareSystem) => (
        <span className="text-gray-300">
          {getFactionName(system.owner_faction_id)}
        </span>
      ),
    },
    {
      key: 'contested',
      header: 'Status',
      sortable: true,
      sortKey: (system: FactionWarfareSystem) => system.contested,
      render: (system: FactionWarfareSystem) => (
        <span
          className={`px-2 py-1 rounded text-xs font-medium capitalize ${getContestedColor(
            system.contested
          )}`}
        >
          {system.contested}
        </span>
      ),
    },
    {
      key: 'victory_points',
      header: 'Victory Points',
      sortable: true,
      sortKey: (system: FactionWarfareSystem) => system.victory_points,
      render: (system: FactionWarfareSystem) => (
        <div className="w-full">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-white">
              {system.victory_points.toLocaleString()} /{' '}
              {system.victory_points_threshold.toLocaleString()}
            </span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full"
              style={{
                width: `${Math.min(
                  (system.victory_points / system.victory_points_threshold) * 100,
                  100
                )}%`,
              }}
            />
          </div>
        </div>
      ),
    },
  ]

  const statsColumns = [
    {
      key: 'faction',
      header: 'Faction',
      sortable: true,
      sortKey: (stat: FactionWarfareStatistics) => stat.faction_id,
      render: (stat: FactionWarfareStatistics) => (
        <span className="text-white font-medium">
          {getFactionName(stat.faction_id)}
        </span>
      ),
    },
    {
      key: 'pilots',
      header: 'Pilots',
      sortable: true,
      sortKey: (stat: FactionWarfareStatistics) => stat.pilots,
      render: (stat: FactionWarfareStatistics) => (
        <span className="text-white">{stat.pilots.toLocaleString()}</span>
      ),
    },
    {
      key: 'systems',
      header: 'Systems Controlled',
      sortable: true,
      sortKey: (stat: FactionWarfareStatistics) => stat.systems_controlled,
      render: (stat: FactionWarfareStatistics) => (
        <span className="text-green-400">
          {stat.systems_controlled.toLocaleString()}
        </span>
      ),
    },
    {
      key: 'kills_week',
      header: 'Kills (Week)',
      sortable: true,
      sortKey: (stat: FactionWarfareStatistics) => stat.kills_last_week,
      render: (stat: FactionWarfareStatistics) => (
        <span className="text-blue-400">
          {stat.kills_last_week.toLocaleString()}
        </span>
      ),
    },
    {
      key: 'kills_total',
      header: 'Total Kills',
      sortable: true,
      sortKey: (stat: FactionWarfareStatistics) => stat.kills_total,
      render: (stat: FactionWarfareStatistics) => (
        <span className="text-purple-400">
          {stat.kills_total.toLocaleString()}
        </span>
      ),
    },
    {
      key: 'vp_week',
      header: 'VP (Week)',
      sortable: true,
      sortKey: (stat: FactionWarfareStatistics) =>
        stat.victory_points_last_week,
      render: (stat: FactionWarfareStatistics) => (
        <span className="text-orange-400">
          {stat.victory_points_last_week.toLocaleString()}
        </span>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">
            Faction Warfare
          </h1>
          <p className="text-gray-400">Track faction warfare systems and statistics</p>
        </div>
        <Button
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
        >
          {syncMutation.isPending ? 'Syncing...' : 'Sync FW Data'}
        </Button>
      </div>

      {/* Summary Statistics */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card title="Total Systems">
            <div className="text-3xl font-bold text-white">
              {summary.total_systems}
            </div>
          </Card>

          <Card title="Contested Systems">
            <div className="text-3xl font-bold text-red-400">
              {summary.contested_systems}
            </div>
          </Card>

          <Card title="Vulnerable Systems">
            <div className="text-3xl font-bold text-yellow-400">
              {summary.vulnerable_systems}
            </div>
          </Card>
        </div>
      )}

      {/* Character FW Status */}
      {characterStats && characterStats.is_enrolled && (
        <Card title="Your Faction Warfare Status">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div>
              <div className="text-sm text-gray-400">Faction</div>
              <div className="text-xl font-bold text-white">
                {getFactionName(characterStats.faction_id || 0)}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Current Rank</div>
              <div className="text-xl font-bold text-blue-400">
                {characterStats.current_rank}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Kills (Week)</div>
              <div className="text-xl font-bold text-green-400">
                {characterStats.kills_last_week}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-400">VP (Week)</div>
              <div className="text-xl font-bold text-purple-400">
                {characterStats.victory_points_last_week.toLocaleString()}
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Tabs */}
      <div className="flex gap-2">
        <Button
          variant={activeTab === 'systems' ? 'primary' : 'secondary'}
          onClick={() => setActiveTab('systems')}
        >
          Systems
        </Button>
        <Button
          variant={activeTab === 'statistics' ? 'primary' : 'secondary'}
          onClick={() => setActiveTab('statistics')}
        >
          Statistics
        </Button>
      </div>

      {/* Systems Tab */}
      {activeTab === 'systems' && (
        <>
          <div className="flex gap-2">
            <Button
              variant={contestedOnly ? 'secondary' : 'primary'}
              size="sm"
              onClick={() => setContestedOnly(false)}
            >
              All Systems
            </Button>
            <Button
              variant={contestedOnly ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => setContestedOnly(true)}
            >
              Contested Only
            </Button>
          </div>

          <Card title="Faction Warfare Systems">
            {systemsLoading ? (
              <TableSkeleton rows={10} columns={5} />
            ) : (
              <Table
                data={systems || []}
                columns={systemColumns}
                keyExtractor={(item) => item.id.toString()}
                emptyMessage="No faction warfare systems found."
                defaultSort={{ key: 'victory_points', direction: 'desc' }}
              />
            )}
          </Card>
        </>
      )}

      {/* Statistics Tab */}
      {activeTab === 'statistics' && (
        <Card title="Faction Statistics">
          {statsLoading ? (
            <TableSkeleton rows={4} columns={6} />
          ) : (
            <Table
              data={statistics || []}
              columns={statsColumns}
              keyExtractor={(item) => item.id.toString()}
              emptyMessage="No faction statistics found."
              defaultSort={{ key: 'systems', direction: 'desc' }}
            />
          )}
        </Card>
      )}
    </div>
  )
}
