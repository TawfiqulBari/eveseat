import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Table } from '../components/common/Table'
import { Button } from '../components/common/Button'
import { Badge } from '../components/common/Badge'
import { TableSkeleton } from '../components/common/Skeleton'
import { useToast } from '../components/common/Toast'
import { useCharacter } from '../hooks/useCharacter'
import { industryService, IndustryJob } from '../services/industry'
import { logger } from '../utils/logger'
import { formatISK } from '../utils/formatters'
import { formatDistanceToNow, format } from 'date-fns'

export default function Industry() {
  const { characterId } = useCharacter()
  const queryClient = useQueryClient()
  const { showToast } = useToast()

  const [filters, setFilters] = useState({
    skip: 0,
    limit: 50,
    activity_id: undefined as number | undefined,
    status: undefined as string | undefined,
  })

  const { data: jobs, isLoading: jobsLoading, error: jobsError } = useQuery({
    queryKey: ['industry-jobs', characterId, filters],
    queryFn: () => industryService.listJobs({
      character_id: characterId || undefined,
      ...filters,
      offset: filters.skip,
    }),
    enabled: !!characterId,
  })

  const { data: facilities, isLoading: facilitiesLoading } = useQuery({
    queryKey: ['industry-facilities', characterId],
    queryFn: () => industryService.listFacilities({
      character_id: characterId || undefined,
    }),
    enabled: !!characterId,
  })

  const { data: statistics, isLoading: statsLoading } = useQuery({
    queryKey: ['industry-statistics', characterId],
    queryFn: () => industryService.getStatistics(characterId!, 30),
    enabled: !!characterId,
  })

  const syncMutation = useMutation({
    mutationFn: () => industryService.triggerSync(characterId!),
    onSuccess: () => {
      showToast('Industry sync started', 'success')
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['industry-jobs'] })
        queryClient.invalidateQueries({ queryKey: ['industry-statistics'] })
      }, 2000)
    },
    onError: (error) => {
      logger.error('Failed to sync industry', error)
      showToast('Failed to sync industry', 'error')
    },
  })

  const getActivityName = (activityId: number) => {
    const activities: Record<number, string> = {
      1: 'Manufacturing',
      3: 'TE Research',
      4: 'ME Research',
      5: 'Copying',
      8: 'Invention',
      9: 'Reverse Engineering',
    }
    return activities[activityId] || `Activity ${activityId}`
  }

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'success' | 'warning' | 'info' | 'danger' | 'secondary'> = {
      active: 'info',
      ready: 'success',
      delivered: 'success',
      paused: 'warning',
      cancelled: 'danger',
      reverted: 'secondary',
    }
    return <Badge variant={variants[status] || 'secondary'}>{status}</Badge>
  }

  const columns = [
    {
      key: 'start_date',
      header: 'Started',
      sortable: true,
      sortKey: (job: IndustryJob) => new Date(job.start_date),
      render: (job: IndustryJob) => (
        <div>
          <div className="text-white text-sm">
            {format(new Date(job.start_date), 'MMM dd, yyyy')}
          </div>
          <div className="text-xs text-gray-400">
            {formatDistanceToNow(new Date(job.start_date), { addSuffix: true })}
          </div>
        </div>
      ),
    },
    {
      key: 'activity',
      header: 'Activity',
      sortable: true,
      sortKey: (job: IndustryJob) => job.activity_id,
      render: (job: IndustryJob) => (
        <Badge variant="info">{getActivityName(job.activity_id)}</Badge>
      ),
    },
    {
      key: 'blueprint',
      header: 'Blueprint',
      sortable: true,
      sortKey: (job: IndustryJob) => job.blueprint_type_id,
      render: (job: IndustryJob) => (
        <span className="text-white">Type {job.blueprint_type_id}</span>
      ),
    },
    {
      key: 'product',
      header: 'Product',
      sortable: true,
      sortKey: (job: IndustryJob) => job.product_type_id || 0,
      render: (job: IndustryJob) => (
        job.product_type_id ? (
          <span className="text-gray-300">Type {job.product_type_id}</span>
        ) : (
          <span className="text-gray-500">-</span>
        )
      ),
    },
    {
      key: 'runs',
      header: 'Runs',
      sortable: true,
      sortKey: (job: IndustryJob) => job.runs,
      render: (job: IndustryJob) => (
        <span className="text-gray-300">{job.runs}</span>
      ),
    },
    {
      key: 'cost',
      header: 'Cost',
      sortable: true,
      sortKey: (job: IndustryJob) => job.cost || 0,
      render: (job: IndustryJob) => (
        job.cost ? (
          <span className="text-yellow-400">{formatISK(job.cost)}</span>
        ) : (
          <span className="text-gray-500">-</span>
        )
      ),
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      sortKey: (job: IndustryJob) => job.status,
      render: (job: IndustryJob) => getStatusBadge(job.status),
    },
    {
      key: 'end_date',
      header: 'Ends',
      sortable: true,
      sortKey: (job: IndustryJob) => new Date(job.end_date),
      render: (job: IndustryJob) => (
        <span className="text-gray-300 text-sm">
          {formatDistanceToNow(new Date(job.end_date), { addSuffix: true })}
        </span>
      ),
    },
  ]

  if (!characterId) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Industry</h1>
          <p className="text-gray-400">Please select a character</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Industry</h1>
          <p className="text-gray-400">Manage your industry jobs and facilities</p>
        </div>
        <Button
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
        >
          {syncMutation.isPending ? 'Syncing...' : 'Sync Industry'}
        </Button>
      </div>

      {/* Statistics */}
      {statsLoading ? (
        <Card title="Industry Statistics">
          <div className="text-gray-400">Loading statistics...</div>
        </Card>
      ) : statistics ? (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
          <Card title="Total Jobs">
            <div className="text-3xl font-bold text-white">{statistics.total_jobs}</div>
          </Card>
          <Card title="Active Jobs">
            <div className="text-3xl font-bold text-yellow-400">{statistics.active_jobs}</div>
          </Card>
          <Card title="Completed">
            <div className="text-3xl font-bold text-green-400">{statistics.completed_jobs}</div>
          </Card>
          <Card title="Total Runs">
            <div className="text-3xl font-bold text-white">{statistics.total_runs}</div>
          </Card>
          <Card title="Total Cost">
            <div className="text-2xl font-bold text-yellow-400">
              {formatISK(statistics.total_cost)}
            </div>
          </Card>
        </div>
      ) : null}

      {/* Activity Breakdown */}
      {statistics && Object.keys(statistics.by_activity).length > 0 && (
        <Card title="By Activity">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Object.entries(statistics.by_activity).map(([activity, stats]) => (
              <div key={activity} className="p-4 bg-eve-darker rounded-lg">
                <div className="text-white font-medium mb-2">{activity}</div>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Jobs:</span>
                    <span className="text-white">{stats.jobs}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Runs:</span>
                    <span className="text-white">{stats.runs}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Cost:</span>
                    <span className="text-yellow-400">{formatISK(stats.cost)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Facilities */}
      {facilitiesLoading ? (
        <Card title="Facilities">
          <div className="text-gray-400">Loading facilities...</div>
        </Card>
      ) : facilities && facilities.length > 0 ? (
        <Card title="Facilities">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {facilities.map((facility) => (
              <div key={facility.id} className="p-4 bg-eve-darker rounded-lg">
                <div className="text-white font-medium">
                  {facility.name || `Facility ${facility.facility_id}`}
                </div>
                <div className="text-sm text-gray-400 mt-1">
                  System: {facility.solar_system_id}
                  {facility.tax !== null && ` • Tax: ${(facility.tax * 100).toFixed(2)}%`}
                </div>
              </div>
            ))}
          </div>
        </Card>
      ) : null}

      {/* Filters */}
      <Card title="Filters">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Activity
            </label>
            <select
              value={filters.activity_id || ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  activity_id: e.target.value ? parseInt(e.target.value) : undefined,
                })
              }
              className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
            >
              <option value="">All Activities</option>
              <option value="1">Manufacturing</option>
              <option value="3">TE Research</option>
              <option value="4">ME Research</option>
              <option value="5">Copying</option>
              <option value="8">Invention</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Status
            </label>
            <select
              value={filters.status || ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  status: e.target.value || undefined,
                })
              }
              className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
            >
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="ready">Ready</option>
              <option value="delivered">Delivered</option>
              <option value="paused">Paused</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Jobs Table */}
      <Card title={`Industry Jobs (${jobs?.length || 0})`}>
        {jobsLoading ? (
          <TableSkeleton rows={10} columns={8} />
        ) : jobsError ? (
          <div className="text-center py-8 text-red-400">
            Error loading industry jobs. Try syncing your industry.
          </div>
        ) : (
          <Table
            data={jobs || []}
            columns={columns}
            keyExtractor={(item) => item.id.toString()}
            emptyMessage="No industry jobs found. Click 'Sync Industry' to fetch from EVE Online."
            defaultSort={{ key: 'start_date', direction: 'desc' }}
          />
        )}
      </Card>
    </div>
  )
}
