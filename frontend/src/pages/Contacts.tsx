import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Table } from '../components/common/Table'
import { Button } from '../components/common/Button'
import { Badge } from '../components/common/Badge'
import { Pagination } from '../components/common/Pagination'
import { TableSkeleton } from '../components/common/Skeleton'
import { useToast } from '../components/common/Toast'
import { useCharacter } from '../hooks/useCharacter'
import { contactsService, Contact, ContactLabel } from '../services/contacts'
import { logger } from '../utils/logger'

export default function Contacts() {
  const { characterId } = useCharacter()
  const queryClient = useQueryClient()
  const { showToast } = useToast()

  const [filters, setFilters] = useState({
    skip: 0,
    limit: 50,
    min_standing: undefined as number | undefined,
    max_standing: undefined as number | undefined,
    contact_type: undefined as string | undefined,
    watched_only: false,
  })

  const { data: contacts, isLoading: contactsLoading, error: contactsError } = useQuery({
    queryKey: ['contacts', characterId, filters],
    queryFn: () => contactsService.listContacts({
      character_id: characterId || undefined,
      ...filters,
      offset: filters.skip,
    }),
    enabled: !!characterId,
  })

  const { data: labels, isLoading: labelsLoading } = useQuery({
    queryKey: ['contact-labels', characterId],
    queryFn: () => contactsService.listLabels(characterId || undefined),
    enabled: !!characterId,
  })

  const syncMutation = useMutation({
    mutationFn: () => contactsService.triggerSync(characterId!),
    onSuccess: () => {
      showToast('Contacts sync started', 'success')
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['contacts'] })
      }, 2000)
    },
    onError: (error) => {
      logger.error('Failed to sync contacts', error)
      showToast('Failed to sync contacts', 'error')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (contactId: number) => contactsService.deleteContact(contactId),
    onSuccess: () => {
      showToast('Contact deleted', 'success')
      queryClient.invalidateQueries({ queryKey: ['contacts'] })
    },
    onError: (error) => {
      logger.error('Failed to delete contact', error)
      showToast('Failed to delete contact', 'error')
    },
  })

  const getStandingColor = (standing: number) => {
    if (standing >= 5) return 'text-blue-400'
    if (standing > 0) return 'text-green-400'
    if (standing === 0) return 'text-gray-400'
    if (standing > -5) return 'text-orange-400'
    return 'text-red-400'
  }

  const getStandingLabel = (standing: number) => {
    if (standing >= 5) return 'Excellent'
    if (standing > 0) return 'Good'
    if (standing === 0) return 'Neutral'
    if (standing > -5) return 'Bad'
    return 'Terrible'
  }

  const columns = [
    {
      key: 'contact_id',
      header: 'Contact ID',
      sortable: true,
      sortKey: (contact: Contact) => contact.contact_id,
      render: (contact: Contact) => (
        <span className="text-white font-medium">{contact.contact_id}</span>
      ),
    },
    {
      key: 'type',
      header: 'Type',
      sortable: true,
      sortKey: (contact: Contact) => contact.contact_type,
      render: (contact: Contact) => (
        <Badge variant="secondary">
          {contact.contact_type}
        </Badge>
      ),
    },
    {
      key: 'standing',
      header: 'Standing',
      sortable: true,
      sortKey: (contact: Contact) => contact.standing,
      render: (contact: Contact) => (
        <div className="flex items-center gap-2">
          <span className={`font-medium ${getStandingColor(contact.standing)}`}>
            {contact.standing.toFixed(1)}
          </span>
          <span className="text-sm text-gray-400">
            ({getStandingLabel(contact.standing)})
          </span>
        </div>
      ),
    },
    {
      key: 'watched',
      header: 'Watched',
      sortable: true,
      sortKey: (contact: Contact) => contact.is_watched ? 1 : 0,
      render: (contact: Contact) => (
        contact.is_watched ? (
          <Badge variant="success">Watched</Badge>
        ) : (
          <span className="text-gray-500">-</span>
        )
      ),
    },
    {
      key: 'blocked',
      header: 'Blocked',
      sortable: true,
      sortKey: (contact: Contact) => contact.is_blocked ? 1 : 0,
      render: (contact: Contact) => (
        contact.is_blocked ? (
          <Badge variant="danger">Blocked</Badge>
        ) : (
          <span className="text-gray-500">-</span>
        )
      ),
    },
    {
      key: 'labels',
      header: 'Labels',
      sortable: false,
      render: (contact: Contact) => (
        <div className="flex gap-1 flex-wrap">
          {contact.label_ids && contact.label_ids.length > 0 ? (
            contact.label_ids.map((labelId) => {
              const label = labels?.find((l: ContactLabel) => l.label_id === labelId)
              return (
                <Badge key={labelId} variant="info" size="sm">
                  {label?.name || `Label ${labelId}`}
                </Badge>
              )
            })
          ) : (
            <span className="text-gray-500">-</span>
          )}
        </div>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      sortable: false,
      render: (contact: Contact) => (
        <Button
          size="sm"
          variant="danger"
          onClick={() => deleteMutation.mutate(contact.id)}
          disabled={deleteMutation.isPending}
        >
          Delete
        </Button>
      ),
    },
  ]

  if (!characterId) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Contacts</h1>
          <p className="text-gray-400">Please select a character</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Contacts</h1>
        <p className="text-gray-400">Manage your character contacts and standings</p>
      </div>

      {/* Contact Labels */}
      {labelsLoading ? (
        <Card title="Contact Labels">
          <div className="text-gray-400">Loading labels...</div>
        </Card>
      ) : labels && labels.length > 0 ? (
        <Card title="Contact Labels">
          <div className="flex gap-2 flex-wrap">
            {labels.map((label: ContactLabel) => (
              <Badge key={label.id} variant="info">
                {label.name} (ID: {label.label_id})
              </Badge>
            ))}
          </div>
        </Card>
      ) : null}

      {/* Filters */}
      <Card title="Filters">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Contact Type
            </label>
            <select
              value={filters.contact_type || ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  contact_type: e.target.value || undefined,
                })
              }
              className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
            >
              <option value="">All Types</option>
              <option value="character">Character</option>
              <option value="corporation">Corporation</option>
              <option value="alliance">Alliance</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Min Standing
            </label>
            <input
              type="number"
              min="-10"
              max="10"
              step="0.1"
              value={filters.min_standing ?? ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  min_standing: e.target.value ? parseFloat(e.target.value) : undefined,
                })
              }
              className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
              placeholder="-10.0"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Max Standing
            </label>
            <input
              type="number"
              min="-10"
              max="10"
              step="0.1"
              value={filters.max_standing ?? ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  max_standing: e.target.value ? parseFloat(e.target.value) : undefined,
                })
              }
              className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
              placeholder="10.0"
            />
          </div>
          <div className="flex items-end">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={filters.watched_only}
                onChange={(e) =>
                  setFilters({
                    ...filters,
                    watched_only: e.target.checked,
                  })
                }
                className="w-4 h-4 text-eve-blue bg-eve-darker border-eve-gray rounded focus:ring-eve-blue"
              />
              <span className="text-sm text-gray-300">Watched Only</span>
            </label>
          </div>
          <div className="flex items-end gap-2">
            <Button
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending}
              className="flex-1"
            >
              {syncMutation.isPending ? 'Syncing...' : 'Sync Contacts'}
            </Button>
          </div>
        </div>
      </Card>

      {/* Contacts Table */}
      <Card title={`Contacts (${contacts?.length || 0})`}>
        {contactsLoading ? (
          <TableSkeleton rows={10} columns={7} />
        ) : contactsError ? (
          <div className="text-center py-8 text-red-400">
            Error loading contacts. Try syncing your contacts.
          </div>
        ) : (
          <Table
            data={contacts || []}
            columns={columns}
            keyExtractor={(item) => item.id.toString()}
            emptyMessage="No contacts found. Click 'Sync Contacts' to fetch from EVE Online."
            defaultSort={{ key: 'standing', direction: 'desc' }}
          />
        )}
      </Card>
    </div>
  )
}
