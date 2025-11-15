import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Table } from '../components/common/Table'
import { Button } from '../components/common/Button'
import { Badge } from '../components/common/Badge'
import { TableSkeleton } from '../components/common/Skeleton'
import { useToast } from '../components/common/Toast'
import { useCharacter } from '../hooks/useCharacter'
import { sovereigntyService, SystemSovereignty, SovereigntyCampaign } from '../services/sovereignty'
import { logger } from '../utils/logger'
import { formatDistanceToNow, format } from 'date-fns'

export default function Sovereignty() {
  const { characterId } = useCharacter()
  const queryClient = useQueryClient()
  const { showToast } = useToast()

  const [activeTab, setActiveTab] = useState<'systems' | 'campaigns'>('systems')
  const [filters, setFilters] = useState({
    alliance_id: undefined as number | undefined,
  })

  const { data: systems, isLoading: systemsLoading, error: systemsError } = useQuery({
    queryKey: ['sov-systems', filters],
    queryFn: () => sovereigntyService.listSystems(filters),
    enabled: !!characterId && activeTab === 'systems',
  })

  const { data: campaigns, isLoading: campaignsLoading, error: campaignsError } = useQuery({
    queryKey: ['sov-campaigns'],
    queryFn: () => sovereigntyService.listCampaigns({}),
    enabled: !!characterId && activeTab === 'campaigns',
  })

  const { data: statistics, isLoading: statsLoading } = useQuery({
    queryKey: ['sov-statistics'],
    queryFn: () => sovereigntyService.getStatistics(),
    enabled: !!characterId,
  })

  const syncMutation = useMutation({
    mutationFn: () => sovereigntyService.triggerSync(),
    onSuccess: () => {
      showToast('Sovereignty sync started', 'success')
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['sov-systems'] })
        queryClient.invalidateQueries({ queryKey: ['sov-campaigns'] })
        queryClient.invalidateQueries({ queryKey: ['sov-statistics'] })
      }, 2000)
    },
    onError: (error) => {
      logger.error('Failed to sync sovereignty', error)
      showToast('Failed to sync sovereignty', 'error')
    },
  })

  const systemColumns = [
    {
      key: 'system_id',
      header: 'System',
      sortable: true,
      sortKey: (system: SystemSovereignty) => system.system_id,
      render: (system: SystemSovereignty) => (
        <span className="text-white">System {system.system_id}</span>
      ),
    },
    {
      key: 'alliance',
      header: 'Alliance',
      sortable: true,
      sortKey: (system: SystemSovereignty) => system.alliance_id || 0,
      render: (system: SystemSovereignty) => (
        system.alliance_id ? (
          <Badge variant="info">Alliance {system.alliance_id}</Badge>
        ) : (
          <span className="text-gray-500">-</span>
        )
      ),
    },
    {
      key: 'corporation',
      header: 'Corporation',
      sortable: true,
      sortKey: (system: SystemSovereignty) => system.corporation_id || 0,
      render: (system: SystemSovereignty) => (
        system.corporation_id ? (
          <span className="text-gray-300">Corp {system.corporation_id}</span>
        ) : (
          <span className="text-gray-500">-</span>
        )
      ),
    },
    {
      key: 'faction',
      header: 'Faction',
      sortable: true,
      sortKey: (system: SystemSovereignty) => system.faction_id || 0,
      render: (system: SystemSovereignty) => (
        system.faction_id ? (
          <Badge variant="secondary">Faction {system.faction_id}</Badge>
        ) : (
          <span className="text-gray-500">-</span>
        )
      ),
    },
  ]

  const campaignColumns = [
    {
      key: 'system',
      header: 'System',
      sortable: true,
      sortKey: (campaign: SovereigntyCampaign) => campaign.system_id,
      render: (campaign: SovereigntyCampaign) => (
        <span className="text-white">System {campaign.system_id}</span>
      ),
    },
    {
      key: 'type',
      header: 'Type',
      sortable: true,
      sortKey: (campaign: SovereigntyCampaign) => campaign.event_type,
      render: (campaign: SovereigntyCampaign) => (
        <Badge variant="warning">{campaign.event_type}</Badge>
      ),
    },
    {
      key: 'defender',
      header: 'Defender',
      sortable: true,
      sortKey: (campaign: SovereigntyCampaign) => campaign.defender_id || 0,
      render: (campaign: SovereigntyCampaign) => (
        campaign.defender_id ? (
          <span className="text-blue-400">Alliance {campaign.defender_id}</span>
        ) : (
          <span className="text-gray-500">-</span>
        )
      ),
    },
    {
      key: 'scores',
      header: 'Score',
      sortable: false,
      render: (campaign: SovereigntyCampaign) => (
        <div className="text-sm">
          <div className="text-blue-400">Defender: {campaign.defender_score.toFixed(1)}%</div>
          <div className="text-red-400">Attackers: {campaign.attackers_score.toFixed(1)}%</div>
        </div>
      ),
    },
    {
      key: 'start',
      header: 'Started',
      sortable: true,
      sortKey: (campaign: SovereigntyCampaign) => new Date(campaign.start_time),
      render: (campaign: SovereigntyCampaign) => (
        <div>
          <div className="text-white text-sm">
            {format(new Date(campaign.start_time), 'MMM dd, HH:mm')}
          </div>
          <div className="text-xs text-gray-400">
            {formatDistanceToNow(new Date(campaign.start_time), { addSuffix: true })}
          </div>
        </div>
      ),
    },
  ]

  if (!characterId) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Sovereignty</h1>
          <p className="text-gray-400">Please select a character</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Sovereignty</h1>
          <p className="text-gray-400">Track sovereignty and ongoing campaigns</p>
        </div>
        <Button
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
        >
          {syncMutation.isPending ? 'Syncing...' : 'Sync Sovereignty'}
        </Button>
      </div>

      {/* Statistics */}
      {statsLoading ? (
        <Card title="Sovereignty Statistics">
          <div className="text-gray-400">Loading statistics...</div>
        </Card>
      ) : statistics ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Card title="Total Systems">
            <div className="text-3xl font-bold text-white">{statistics.total_systems}</div>
          </Card>
          <Card title="Vulnerable Structures">
            <div className="text-3xl font-bold text-red-400">{statistics.vulnerable_structures}</div>
          </Card>
          <Card title="Active Campaigns">
            <div className="text-3xl font-bold text-yellow-400">{statistics.active_campaigns}</div>
          </Card>
          <Card title="Alliances">
            <div className="text-3xl font-bold text-blue-400">
              {Object.keys(statistics.systems_by_alliance).length}
            </div>
          </Card>
        </div>
      ) : null}

      {/* Filters */}
      {activeTab === 'systems' && (
        <Card title="Filters">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Alliance ID
              </label>
              <input
                type="number"
                value={filters.alliance_id || ''}
                onChange={(e) =>
                  setFilters({
                    ...filters,
                    alliance_id: e.target.value ? parseInt(e.target.value) : undefined,
                  })
                }
                className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
                placeholder="Filter by alliance..."
              />
            </div>
          </div>
        </Card>
      )}

      {/* Tabs */}
      <Card>
        <div className="flex gap-4 border-b border-eve-gray pb-4">
          <button
            onClick={() => setActiveTab('systems')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'systems'
                ? 'bg-eve-blue text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Systems
          </button>
          <button
            onClick={() => setActiveTab('campaigns')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'campaigns'
                ? 'bg-eve-blue text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Campaigns
          </button>
        </div>

        {/* Systems Tab */}
        {activeTab === 'systems' && (
          <div className="mt-6">
            {systemsLoading ? (
              <TableSkeleton rows={10} columns={4} />
            ) : systemsError ? (
              <div className="text-center py-8 text-red-400">
                Error loading systems. Try syncing sovereignty.
              </div>
            ) : (
              <Table
                data={systems || []}
                columns={systemColumns}
                keyExtractor={(item) => item.id.toString()}
                emptyMessage="No sovereignty data found. Click 'Sync Sovereignty' to fetch from EVE Online."
                defaultSort={{ key: 'system_id', direction: 'asc' }}
              />
            )}
          </div>
        )}

        {/* Campaigns Tab */}
        {activeTab === 'campaigns' && (
          <div className="mt-6">
            {campaignsLoading ? (
              <TableSkeleton rows={10} columns={5} />
            ) : campaignsError ? (
              <div className="text-center py-8 text-red-400">
                Error loading campaigns. Try syncing sovereignty.
              </div>
            ) : (
              <Table
                data={campaigns || []}
                columns={campaignColumns}
                keyExtractor={(item) => item.id.toString()}
                emptyMessage="No active campaigns found."
                defaultSort={{ key: 'start', direction: 'desc' }}
              />
            )}
          </div>
        )}
      </Card>
    </div>
  )
}
