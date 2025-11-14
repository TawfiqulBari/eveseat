import React, { useState } from 'react'
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Table } from '../components/common/Table'
import { Button } from '../components/common/Button'
import { Badge } from '../components/common/Badge'
import { Pagination } from '../components/common/Pagination'
import { TableSkeleton } from '../components/common/Skeleton'
import { Modal } from '../components/common/Modal'
import { useToast } from '../components/common/Toast'
import { useCharacter } from '../hooks/useCharacter'
import { contractsService, Contract, ContractItem, ContractDetail } from '../services/contracts'
import { logger } from '../utils/logger'
import { formatISK } from '../utils/formatters'
import { formatDistanceToNow, format } from 'date-fns'

export default function Contracts() {
  const { characterId } = useCharacter()
  const queryClient = useQueryClient()
  const { showToast } = useToast()

  const [filters, setFilters] = useState({
    skip: 0,
    limit: 50,
    contract_type: undefined as string | undefined,
    status: undefined as string | undefined,
  })

  const [selectedContract, setSelectedContract] = useState<ContractDetail | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  const { data: contracts, isLoading: contractsLoading, error: contractsError } = useQuery({
    queryKey: ['contracts', characterId, filters],
    queryFn: () => contractsService.listContracts({
      character_id: characterId || undefined,
      ...filters,
      offset: filters.skip,
    }),
    enabled: !!characterId,
  })

  const { data: statistics, isLoading: statsLoading } = useQuery({
    queryKey: ['contract-statistics', characterId],
    queryFn: () => contractsService.getStatistics(characterId!),
    enabled: !!characterId,
  })

  const syncMutation = useMutation({
    mutationFn: () => contractsService.triggerSync(characterId!),
    onSuccess: () => {
      showToast('Contracts sync started', 'success')
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['contracts'] })
        queryClient.invalidateQueries({ queryKey: ['contract-statistics'] })
      }, 2000)
    },
    onError: (error) => {
      logger.error('Failed to sync contracts', error)
      showToast('Failed to sync contracts', 'error')
    },
  })

  const handleViewDetails = async (contractId: number) => {
    try {
      const detail = await contractsService.getContract(contractId)
      setSelectedContract(detail)
      setIsModalOpen(true)
    } catch (error) {
      logger.error('Failed to load contract details', error)
      showToast('Failed to load contract details', 'error')
    }
  }

  const getTypeBadge = (type: string) => {
    const variants: Record<string, 'success' | 'warning' | 'info' | 'secondary'> = {
      item_exchange: 'success',
      auction: 'warning',
      courier: 'info',
      loan: 'secondary',
    }
    return <Badge variant={variants[type] || 'secondary'}>{type}</Badge>
  }

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'success' | 'warning' | 'danger' | 'secondary'> = {
      outstanding: 'warning',
      in_progress: 'info',
      finished_issuer: 'success',
      finished_contractor: 'success',
      finished: 'success',
      cancelled: 'danger',
      rejected: 'danger',
      failed: 'danger',
      deleted: 'secondary',
      reversed: 'secondary',
    }
    return <Badge variant={variants[status] || 'secondary'}>{status}</Badge>
  }

  const columns = [
    {
      key: 'date_issued',
      header: 'Issued',
      sortable: true,
      sortKey: (contract: Contract) => new Date(contract.date_issued),
      render: (contract: Contract) => (
        <div>
          <div className="text-white text-sm">
            {format(new Date(contract.date_issued), 'MMM dd, yyyy')}
          </div>
          <div className="text-xs text-gray-400">
            {formatDistanceToNow(new Date(contract.date_issued), { addSuffix: true })}
          </div>
        </div>
      ),
    },
    {
      key: 'type',
      header: 'Type',
      sortable: true,
      sortKey: (contract: Contract) => contract.type,
      render: (contract: Contract) => getTypeBadge(contract.type),
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      sortKey: (contract: Contract) => contract.status,
      render: (contract: Contract) => getStatusBadge(contract.status),
    },
    {
      key: 'availability',
      header: 'Availability',
      sortable: true,
      sortKey: (contract: Contract) => contract.availability,
      render: (contract: Contract) => (
        <Badge variant="secondary">{contract.availability}</Badge>
      ),
    },
    {
      key: 'price',
      header: 'Price',
      sortable: true,
      sortKey: (contract: Contract) => contract.price || 0,
      render: (contract: Contract) => (
        contract.price ? (
          <span className="text-yellow-400 font-medium">{formatISK(contract.price)}</span>
        ) : (
          <span className="text-gray-500">-</span>
        )
      ),
    },
    {
      key: 'reward',
      header: 'Reward',
      sortable: true,
      sortKey: (contract: Contract) => contract.reward || 0,
      render: (contract: Contract) => (
        contract.reward ? (
          <span className="text-green-400 font-medium">{formatISK(contract.reward)}</span>
        ) : (
          <span className="text-gray-500">-</span>
        )
      ),
    },
    {
      key: 'collateral',
      header: 'Collateral',
      sortable: true,
      sortKey: (contract: Contract) => contract.collateral || 0,
      render: (contract: Contract) => (
        contract.collateral ? (
          <span className="text-orange-400 font-medium">{formatISK(contract.collateral)}</span>
        ) : (
          <span className="text-gray-500">-</span>
        )
      ),
    },
    {
      key: 'expires',
      header: 'Expires',
      sortable: true,
      sortKey: (contract: Contract) => new Date(contract.date_expired),
      render: (contract: Contract) => (
        <span className="text-gray-300 text-sm">
          {formatDistanceToNow(new Date(contract.date_expired), { addSuffix: true })}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      sortable: false,
      render: (contract: Contract) => (
        <Button
          size="sm"
          variant="secondary"
          onClick={() => handleViewDetails(contract.contract_id)}
        >
          View Details
        </Button>
      ),
    },
  ]

  if (!characterId) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Contracts</h1>
          <p className="text-gray-400">Please select a character</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Contracts</h1>
        <p className="text-gray-400">Manage your character's contracts</p>
      </div>

      {/* Statistics */}
      {statsLoading ? (
        <Card title="Contract Statistics">
          <div className="text-gray-400">Loading statistics...</div>
        </Card>
      ) : statistics ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Card title="Total Contracts">
            <div className="text-3xl font-bold text-white">{statistics.total_contracts || 0}</div>
          </Card>
          <Card title="Active Contracts">
            <div className="text-3xl font-bold text-yellow-400">{statistics.active_contracts || 0}</div>
          </Card>
          <Card title="Completed">
            <div className="text-3xl font-bold text-green-400">{statistics.completed_contracts || 0}</div>
          </Card>
          <Card title="Failed/Cancelled">
            <div className="text-3xl font-bold text-red-400">{statistics.failed_contracts || 0}</div>
          </Card>
        </div>
      ) : null}

      {/* Filters */}
      <Card title="Filters">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Contract Type
            </label>
            <select
              value={filters.contract_type || ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  contract_type: e.target.value || undefined,
                })
              }
              className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
            >
              <option value="">All Types</option>
              <option value="item_exchange">Item Exchange</option>
              <option value="auction">Auction</option>
              <option value="courier">Courier</option>
              <option value="loan">Loan</option>
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
              <option value="outstanding">Outstanding</option>
              <option value="in_progress">In Progress</option>
              <option value="finished">Finished</option>
              <option value="cancelled">Cancelled</option>
              <option value="rejected">Rejected</option>
              <option value="failed">Failed</option>
            </select>
          </div>
          <div className="flex items-end gap-2">
            <Button
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending}
              className="flex-1"
            >
              {syncMutation.isPending ? 'Syncing...' : 'Sync Contracts'}
            </Button>
          </div>
        </div>
      </Card>

      {/* Contracts Table */}
      <Card title={`Contracts (${contracts?.length || 0})`}>
        {contractsLoading ? (
          <TableSkeleton rows={10} columns={9} />
        ) : contractsError ? (
          <div className="text-center py-8 text-red-400">
            Error loading contracts. Try syncing your contracts.
          </div>
        ) : (
          <Table
            data={contracts || []}
            columns={columns}
            keyExtractor={(item) => item.id.toString()}
            emptyMessage="No contracts found. Click 'Sync Contracts' to fetch from EVE Online."
            defaultSort={{ key: 'date_issued', direction: 'desc' }}
          />
        )}
      </Card>

      {/* Contract Detail Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          setSelectedContract(null)
        }}
        title="Contract Details"
        size="lg"
      >
        {selectedContract && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-gray-400">Type:</span>
                <div className="mt-1">{getTypeBadge(selectedContract.type)}</div>
              </div>
              <div>
                <span className="text-gray-400">Status:</span>
                <div className="mt-1">{getStatusBadge(selectedContract.status)}</div>
              </div>
              <div>
                <span className="text-gray-400">Price:</span>
                <div className="mt-1 text-yellow-400 font-medium">
                  {selectedContract.price ? formatISK(selectedContract.price) : '-'}
                </div>
              </div>
              <div>
                <span className="text-gray-400">Reward:</span>
                <div className="mt-1 text-green-400 font-medium">
                  {selectedContract.reward ? formatISK(selectedContract.reward) : '-'}
                </div>
              </div>
              <div>
                <span className="text-gray-400">Collateral:</span>
                <div className="mt-1 text-orange-400 font-medium">
                  {selectedContract.collateral ? formatISK(selectedContract.collateral) : '-'}
                </div>
              </div>
              <div>
                <span className="text-gray-400">Volume:</span>
                <div className="mt-1 text-white">
                  {selectedContract.volume ? `${selectedContract.volume.toLocaleString()} m³` : '-'}
                </div>
              </div>
            </div>

            {selectedContract.items && selectedContract.items.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold text-white mb-3">Contract Items</h3>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {selectedContract.items.map((item: ContractItem, idx: number) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-3 bg-eve-darker rounded-lg"
                    >
                      <div>
                        <div className="text-white">Type ID: {item.type_id}</div>
                        <div className="text-sm text-gray-400">
                          {item.is_included ? 'Included' : 'Requested'} • {item.is_singleton ? 'Singleton' : 'Stack'}
                        </div>
                      </div>
                      <div className="text-white font-medium">
                        Qty: {item.quantity.toLocaleString()}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
