import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Table } from '../components/common/Table'
import { Button } from '../components/common/Button'
import { Badge } from '../components/common/Badge'
import { TableSkeleton } from '../components/common/Skeleton'
import { useToast } from '../components/common/Toast'
import { useCharacter } from '../hooks/useCharacter'
import { calendarService, CalendarEvent } from '../services/calendar'
import { logger } from '../utils/logger'
import { formatDistanceToNow, format } from 'date-fns'

export default function Calendar() {
  const { characterId } = useCharacter()
  const queryClient = useQueryClient()
  const { showToast } = useToast()

  const [filters, setFilters] = useState({
    skip: 0,
    limit: 50,
    from_date: undefined as string | undefined,
    to_date: undefined as string | undefined,
    response_filter: undefined as string | undefined,
  })

  const { data: events, isLoading: eventsLoading, error: eventsError } = useQuery({
    queryKey: ['calendar-events', characterId, filters],
    queryFn: () => calendarService.listEvents({
      character_id: characterId || undefined,
      ...filters,
      offset: filters.skip,
    }),
    enabled: !!characterId,
  })

  const { data: upcomingEvents, isLoading: upcomingLoading } = useQuery({
    queryKey: ['calendar-upcoming', characterId],
    queryFn: () => calendarService.getUpcomingEvents(characterId || undefined, 7),
    enabled: !!characterId,
  })

  const syncMutation = useMutation({
    mutationFn: () => calendarService.triggerSync(characterId!),
    onSuccess: () => {
      showToast('Calendar sync started', 'success')
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['calendar-events'] })
        queryClient.invalidateQueries({ queryKey: ['calendar-upcoming'] })
      }, 2000)
    },
    onError: (error) => {
      logger.error('Failed to sync calendar', error)
      showToast('Failed to sync calendar', 'error')
    },
  })

  const respondMutation = useMutation({
    mutationFn: ({ eventId, response }: { eventId: number; response: string }) =>
      calendarService.respondToEvent(eventId, characterId!, response),
    onSuccess: () => {
      showToast('Response submitted', 'success')
      queryClient.invalidateQueries({ queryKey: ['calendar-events'] })
      queryClient.invalidateQueries({ queryKey: ['calendar-upcoming'] })
    },
    onError: (error) => {
      logger.error('Failed to respond to event', error)
      showToast('Failed to respond to event', 'error')
    },
  })

  const getResponseBadge = (response: string | null) => {
    if (!response) return <Badge variant="secondary">Not Responded</Badge>
    switch (response.toLowerCase()) {
      case 'accepted':
        return <Badge variant="success">Accepted</Badge>
      case 'declined':
        return <Badge variant="danger">Declined</Badge>
      case 'tentative':
        return <Badge variant="warning">Tentative</Badge>
      default:
        return <Badge variant="secondary">{response}</Badge>
    }
  }

  const getImportanceBadge = (importance: number) => {
    if (importance >= 2) return <Badge variant="danger">High</Badge>
    if (importance === 1) return <Badge variant="warning">Medium</Badge>
    return <Badge variant="secondary">Low</Badge>
  }

  const columns = [
    {
      key: 'event_date',
      header: 'Date',
      sortable: true,
      sortKey: (event: CalendarEvent) => new Date(event.event_date),
      render: (event: CalendarEvent) => (
        <div>
          <div className="text-white font-medium">
            {format(new Date(event.event_date), 'MMM dd, yyyy HH:mm')}
          </div>
          <div className="text-sm text-gray-400">
            {formatDistanceToNow(new Date(event.event_date), { addSuffix: true })}
          </div>
        </div>
      ),
    },
    {
      key: 'title',
      header: 'Title',
      sortable: true,
      sortKey: (event: CalendarEvent) => event.title,
      render: (event: CalendarEvent) => (
        <div>
          <div className="text-white font-medium">{event.title}</div>
          {event.description && (
            <div className="text-sm text-gray-400 mt-1 line-clamp-2">
              {event.description}
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'duration',
      header: 'Duration',
      sortable: true,
      sortKey: (event: CalendarEvent) => event.duration,
      render: (event: CalendarEvent) => (
        <span className="text-gray-300">
          {event.duration} min
        </span>
      ),
    },
    {
      key: 'importance',
      header: 'Importance',
      sortable: true,
      sortKey: (event: CalendarEvent) => event.importance,
      render: (event: CalendarEvent) => getImportanceBadge(event.importance),
    },
    {
      key: 'owner',
      header: 'Owner',
      sortable: true,
      sortKey: (event: CalendarEvent) => event.owner_name,
      render: (event: CalendarEvent) => (
        <div>
          <div className="text-white">{event.owner_name}</div>
          <div className="text-sm text-gray-400">{event.owner_type}</div>
        </div>
      ),
    },
    {
      key: 'response',
      header: 'Your Response',
      sortable: true,
      sortKey: (event: CalendarEvent) => event.response || '',
      render: (event: CalendarEvent) => getResponseBadge(event.response),
    },
    {
      key: 'actions',
      header: 'Actions',
      sortable: false,
      render: (event: CalendarEvent) => (
        <div className="flex gap-2">
          {(!event.response || event.response !== 'accepted') && (
            <Button
              size="sm"
              variant="success"
              onClick={() =>
                respondMutation.mutate({
                  eventId: event.event_id,
                  response: 'accepted',
                })
              }
              disabled={respondMutation.isPending}
            >
              Accept
            </Button>
          )}
          {(!event.response || event.response !== 'declined') && (
            <Button
              size="sm"
              variant="danger"
              onClick={() =>
                respondMutation.mutate({
                  eventId: event.event_id,
                  response: 'declined',
                })
              }
              disabled={respondMutation.isPending}
            >
              Decline
            </Button>
          )}
        </div>
      ),
    },
  ]

  if (!characterId) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Calendar</h1>
          <p className="text-gray-400">Please select a character</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Calendar</h1>
        <p className="text-gray-400">Manage your character's calendar events</p>
      </div>

      {/* Upcoming Events */}
      {upcomingLoading ? (
        <Card title="Upcoming Events (Next 7 Days)">
          <div className="text-gray-400">Loading upcoming events...</div>
        </Card>
      ) : upcomingEvents && upcomingEvents.length > 0 ? (
        <Card title="Upcoming Events (Next 7 Days)">
          <div className="space-y-3">
            {upcomingEvents.slice(0, 5).map((event: CalendarEvent) => (
              <div
                key={event.id}
                className="flex items-center justify-between p-3 bg-eve-darker rounded-lg"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-white font-medium">{event.title}</span>
                    {getImportanceBadge(event.importance)}
                    {getResponseBadge(event.response)}
                  </div>
                  <div className="text-sm text-gray-400 mt-1">
                    {format(new Date(event.event_date), 'MMM dd, yyyy HH:mm')} • {event.duration} min
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      ) : null}

      {/* Filters */}
      <Card title="Filters">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              From Date
            </label>
            <input
              type="date"
              value={filters.from_date || ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  from_date: e.target.value || undefined,
                })
              }
              className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              To Date
            </label>
            <input
              type="date"
              value={filters.to_date || ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  to_date: e.target.value || undefined,
                })
              }
              className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Response Filter
            </label>
            <select
              value={filters.response_filter || ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  response_filter: e.target.value || undefined,
                })
              }
              className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
            >
              <option value="">All Responses</option>
              <option value="accepted">Accepted</option>
              <option value="declined">Declined</option>
              <option value="tentative">Tentative</option>
              <option value="not_responded">Not Responded</option>
            </select>
          </div>
          <div className="flex items-end gap-2">
            <Button
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending}
              className="flex-1"
            >
              {syncMutation.isPending ? 'Syncing...' : 'Sync Calendar'}
            </Button>
          </div>
        </div>
      </Card>

      {/* Events Table */}
      <Card title={`Calendar Events (${events?.length || 0})`}>
        {eventsLoading ? (
          <TableSkeleton rows={10} columns={7} />
        ) : eventsError ? (
          <div className="text-center py-8 text-red-400">
            Error loading calendar events. Try syncing your calendar.
          </div>
        ) : (
          <Table
            data={events || []}
            columns={columns}
            keyExtractor={(item) => item.id.toString()}
            emptyMessage="No calendar events found. Click 'Sync Calendar' to fetch from EVE Online."
            defaultSort={{ key: 'event_date', direction: 'asc' }}
          />
        )}
      </Card>
    </div>
  )
}
