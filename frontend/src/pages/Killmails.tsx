import React, { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Table } from '../components/common/Table'
import { Button } from '../components/common/Button'
import { DateRangePicker } from '../components/common/DateRangePicker'
import { Pagination } from '../components/common/Pagination'
import { TableSkeleton } from '../components/common/Skeleton'
import { Tooltip } from '../components/common/Tooltip'
import { useToast } from '../components/common/Toast'
import { KillmailDetailModal } from '../components/killmails/KillmailDetailModal'
import { killmailsService, Killmail, KillmailDetail } from '../services/killmails'
import { useKillmailFeed } from '../hooks/useWebSocket'
import { logger } from '../utils/logger'
import { formatISK } from '../utils/formatters'
import { downloadCSV, downloadJSON } from '../utils/export'
import { formatDistanceToNow } from 'date-fns'

export default function Killmails() {
  const [filters, setFilters] = useState({
    skip: 0,
    limit: 50,
    system_id: undefined as number | undefined,
    corporation_id: undefined as number | undefined,
    min_value: undefined as number | undefined,
    start_date: undefined as string | undefined,
    end_date: undefined as string | undefined,
  })
  const [selectedKillmail, setSelectedKillmail] = useState<KillmailDetail | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  // Default date range (last 30 days)
  const getDefaultStartDate = () => {
    const date = new Date()
    date.setDate(date.getDate() - 30)
    return date.toISOString().split('T')[0]
  }

  const getDefaultEndDate = () => {
    return new Date().toISOString().split('T')[0]
  }

  const queryClient = useQueryClient()
  const { showToast } = useToast()
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['killmails', filters],
    queryFn: () => killmailsService.list(filters),
  })

  // Subscribe to real-time killmail updates
  useKillmailFeed({
    onKillmail: (killmailData) => {
      // Invalidate queries to refetch with new killmail
      queryClient.invalidateQueries({ queryKey: ['killmails'] })
      // Show notification
      const victimName = killmailData?.victim?.character?.name || 'Unknown'
      const systemName = killmailData?.solar_system_id || 'Unknown System'
      showToast(`New killmail: ${victimName} in ${systemName}`, 'info', 5000)
    },
    onConnect: () => {
      showToast('Connected to real-time killmail feed', 'success', 3000)
    },
    onDisconnect: () => {
      showToast('Disconnected from killmail feed', 'warning', 3000)
    },
  })

  const columns = [
    {
      key: 'time',
      header: 'Time',
      sortable: true,
      sortKey: (killmail: Killmail) => new Date(killmail.time),
      render: (killmail: Killmail) => (
        <span className="text-gray-300">
          {formatDistanceToNow(new Date(killmail.time), { addSuffix: true })}
        </span>
      ),
    },
    {
      key: 'victim',
      header: 'Victim',
      sortable: true,
      sortKey: (killmail: Killmail) => killmail.victim_character_name || '',
      render: (killmail: Killmail) => (
        <div>
          <div className="text-white font-medium">
            {killmail.victim_character_name || 'Unknown'}
          </div>
          {killmail.victim_corporation_name && (
            <div className="text-sm text-gray-400">{killmail.victim_corporation_name}</div>
          )}
        </div>
      ),
    },
    {
      key: 'system',
      header: 'System',
      sortable: true,
      sortKey: (killmail: Killmail) => killmail.system_name || '',
      render: (killmail: Killmail) => (
        <span className="text-eve-blue">{killmail.system_name || 'Unknown'}</span>
      ),
    },
    {
      key: 'ship',
      header: 'Ship',
      sortable: true,
      sortKey: (killmail: Killmail) => killmail.victim_ship_type_name || '',
      render: (killmail: Killmail) => (
        <span className="text-gray-300">{killmail.victim_ship_type_name || 'Unknown'}</span>
      ),
    },
    {
      key: 'value',
      header: 'Value',
      sortable: true,
      sortKey: (killmail: Killmail) => killmail.value || 0,
      render: (killmail: Killmail) => (
        killmail.value ? (
          <span className="text-yellow-400 font-medium">
            {formatISK(killmail.value)}
          </span>
        ) : (
          <span className="text-gray-500">N/A</span>
        )
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      sortable: false,
      render: (killmail: Killmail) => (
        <div className="flex gap-2">
          <button
            onClick={async () => {
              try {
                const detail = await killmailsService.get(killmail.killmail_id)
                setSelectedKillmail(detail)
                setIsModalOpen(true)
              } catch (error) {
                logger.error('Failed to load killmail details', error, {
                  killmailId: killmail.killmail_id,
                })
                showToast('Failed to load killmail details', 'error')
              }
            }}
            className="text-eve-blue hover:text-eve-blue-dark"
          >
            View Details
          </button>
          {killmail.zkill_url && (
            <a
              href={killmail.zkill_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-eve-blue hover:text-eve-blue-dark"
            >
              zKill
            </a>
          )}
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Killmails</h1>
        <p className="text-gray-400">Track and analyze killmail data</p>
      </div>

      {/* Filters */}
      <Card title="Filters">
        <div className="space-y-4">
          <DateRangePicker
            startDate={filters.start_date || getDefaultStartDate()}
            endDate={filters.end_date || getDefaultEndDate()}
            onStartDateChange={(date) => setFilters({ ...filters, start_date: date })}
            onEndDateChange={(date) => setFilters({ ...filters, end_date: date })}
          />
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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
                    system_id: e.target.value ? parseInt(e.target.value, 10) : undefined,
                  })
                }
                className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
                placeholder="System ID"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Corporation ID
              </label>
              <input
                type="number"
                value={filters.corporation_id || ''}
                onChange={(e) =>
                  setFilters({
                    ...filters,
                    corporation_id: e.target.value ? parseInt(e.target.value, 10) : undefined,
                  })
                }
                className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
                placeholder="Corporation ID"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Min Value (M ISK)
              </label>
              <input
                type="number"
                value={filters.min_value ? filters.min_value / 1000000 : ''}
                onChange={(e) =>
                  setFilters({
                    ...filters,
                    min_value: e.target.value ? parseInt(e.target.value, 10) * 1000000 : undefined,
                  })
                }
                className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
                placeholder="Min Value"
              />
            </div>
            <div className="flex items-end gap-2">
              <Button onClick={() => refetch()} className="flex-1">
                Apply Filters
              </Button>
            </div>
          </div>
        </div>
      </Card>

      {/* Killmails Table */}
      <Card
        title={`Killmails (${data?.total || 0})`}
        actions={
          data && data.items.length > 0 ? (
            <div className="flex gap-2">
              <Tooltip content="Export killmails data as a CSV file">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => {
                    if (data.items) {
                      downloadCSV(
                        data.items.map((km) => ({
                          'Killmail ID': km.killmail_id,
                          'Time': km.time,
                          'Victim': km.victim_character_name || 'Unknown',
                          'Corporation': km.victim_corporation_name || 'Unknown',
                          'Ship': km.victim_ship_type_name || 'Unknown',
                          'System': km.system_name || 'Unknown',
                          'Value (ISK)': km.value || 0,
                        })),
                        'killmails-export',
                        ['Killmail ID', 'Time', 'Victim', 'Corporation', 'Ship', 'System', 'Value (ISK)']
                      )
                      showToast('Killmails exported to CSV', 'success')
                    }
                  }}
                >
                  Export CSV
                </Button>
              </Tooltip>
              <Tooltip content="Export killmails data as a JSON file">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => {
                    if (data.items) {
                      downloadJSON(data.items, 'killmails-export')
                      showToast('Killmails exported to JSON', 'success')
                    }
                  }}
                >
                  Export JSON
                </Button>
              </Tooltip>
            </div>
          ) : undefined
        }
      >
        {isLoading ? (
          <TableSkeleton rows={10} columns={6} />
        ) : error ? (
          <div className="text-center py-8 text-red-400">Error loading killmails</div>
        ) : (
          <>
            <Table
              data={data?.items || []}
              columns={columns}
              keyExtractor={(item) => item.id.toString()}
              emptyMessage="No killmails found"
              defaultSort={{ key: 'time', direction: 'desc' }}
            />
            {data && data.total > 0 && (
              <div className="mt-4">
                <Pagination
                  currentPage={Math.floor(filters.skip / filters.limit) + 1}
                  totalPages={Math.ceil(data.total / filters.limit)}
                  totalItems={data.total}
                  pageSize={filters.limit}
                  onPageChange={(page) => setFilters({ ...filters, skip: (page - 1) * filters.limit })}
                  onPageSizeChange={(size) => setFilters({ ...filters, limit: size, skip: 0 })}
                />
              </div>
            )}
          </>
        )}
      </Card>

      {/* Killmail Detail Modal */}
      <KillmailDetailModal
        killmail={selectedKillmail}
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          setSelectedKillmail(null)
        }}
      />
    </div>
  )
}
