import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Table } from '../components/common/Table'
import { Button } from '../components/common/Button'
import { Pagination } from '../components/common/Pagination'
import { TableSkeleton } from '../components/common/Skeleton'
import { Tooltip } from '../components/common/Tooltip'
import { useToast } from '../components/common/Toast'
import { useCharacter } from '../hooks/useCharacter'
import { formatISK } from '../utils/formatters'
import { downloadCSV, downloadJSON } from '../utils/export'
import { charactersService, CharacterMarketOrder } from '../services/characters'

export default function Market() {
  const { showToast } = useToast()
  const { characterId } = useCharacter()
  const [filters, setFilters] = useState({
    is_buy_order: undefined as boolean | undefined,
    is_active: undefined as boolean | undefined,
    skip: 0,
    limit: 50,
  })

  const { data, isLoading, error, refetch } = useQuery<{
    items: CharacterMarketOrder[]
    total: number
    skip: number
    limit: number
  }>({
    queryKey: ['character-market-orders', characterId, filters],
    queryFn: () => charactersService.getMarketOrders(characterId!, filters),
    enabled: !!characterId && characterId > 0,
    onError: (err: any) => {
      showToast(err.response?.data?.detail || 'Failed to load market orders', 'error')
    },
  })

  const columns = [
    {
      key: 'type_name',
      header: 'Item',
      sortable: true,
      sortKey: (order: CharacterMarketOrder) => order.type_name || `Type ${order.type_id}`,
      render: (order: CharacterMarketOrder) => (
        <div className="flex items-center gap-2">
          {order.type_icon_url && (
            <img
              src={order.type_icon_url}
              alt={order.type_name || `Type ${order.type_id}`}
              className="w-8 h-8 object-contain"
              onError={(e) => {
                // Hide image if it fails to load
                (e.target as HTMLImageElement).style.display = 'none'
              }}
            />
          )}
          <span className="text-white font-medium">{order.type_name || `Type ${order.type_id}`}</span>
        </div>
      ),
    },
    {
      key: 'location',
      header: 'Location',
      sortable: true,
      sortKey: (order: CharacterMarketOrder) => order.location_name || `Location ${order.location_id}`,
      render: (order: CharacterMarketOrder) => (
        <div>
          <div className="text-white">{order.location_name || `Location ${order.location_id}`}</div>
          {order.system_name && (
            <div className="text-sm text-gray-400">{order.system_name}</div>
          )}
          {order.region_name && (
            <div className="text-xs text-gray-500">{order.region_name}</div>
          )}
        </div>
      ),
    },
    {
      key: 'price',
      header: 'Price',
      sortable: true,
      sortKey: (order: CharacterMarketOrder) => order.price,
      render: (order: CharacterMarketOrder) => (
        <span className="text-yellow-400 font-medium">
          {formatISK(order.price)}
        </span>
      ),
    },
    {
      key: 'volume',
      header: 'Volume',
      sortable: true,
      sortKey: (order: CharacterMarketOrder) => order.volume_remain,
      render: (order: CharacterMarketOrder) => (
        <div>
          <div className="text-white">{order.volume_remain.toLocaleString()}</div>
          <div className="text-sm text-gray-400">of {order.volume_total.toLocaleString()}</div>
        </div>
      ),
    },
    {
      key: 'order_type',
      header: 'Type',
      sortable: true,
      sortKey: (order: CharacterMarketOrder) => order.is_buy_order ? 'Buy' : 'Sell',
      render: (order: CharacterMarketOrder) => (
        <span className={`px-2 py-1 rounded text-xs font-medium ${
          order.is_buy_order
            ? 'bg-green-900/30 text-green-400'
            : 'bg-red-900/30 text-red-400'
        }`}>
          {order.is_buy_order ? 'Buy' : 'Sell'}
        </span>
      ),
    },
    {
      key: 'expires',
      header: 'Expires',
      sortable: true,
      sortKey: (order: CharacterMarketOrder) => order.expires ? new Date(order.expires) : new Date(0),
      render: (order: CharacterMarketOrder) => (
        <span className="text-gray-400">
          {order.expires ? new Date(order.expires).toLocaleDateString() : 'N/A'}
        </span>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Market</h1>
        <p className="text-gray-400">Track market orders and prices</p>
      </div>

      {/* Filters */}
      <Card title="Filters">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Order Type
            </label>
            <select
              value={filters.is_buy_order === undefined ? '' : filters.is_buy_order.toString()}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  is_buy_order: e.target.value === '' ? undefined : e.target.value === 'true',
                })
              }
              className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
            >
              <option value="">All</option>
              <option value="true">Buy Orders</option>
              <option value="false">Sell Orders</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Status
            </label>
            <select
              value={filters.is_active === undefined ? '' : filters.is_active.toString()}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  is_active: e.target.value === '' ? undefined : e.target.value === 'true',
                })
              }
              className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
            >
              <option value="">All</option>
              <option value="true">Active</option>
              <option value="false">Inactive</option>
            </select>
          </div>
          <div className="flex items-end">
            <Button onClick={() => refetch()} className="w-full">
              Apply Filters
            </Button>
          </div>
          <div className="flex items-end">
            {characterId && (
              <Button
                variant="secondary"
                onClick={() => {
                  charactersService.syncMarketOrders(characterId!).then(() => {
                    showToast('Market orders sync started', 'success')
                    refetch()
                  }).catch((err) => {
                    showToast(err.response?.data?.detail || 'Failed to sync market orders', 'error')
                  })
                }}
                className="w-full"
              >
                Sync Orders
              </Button>
            )}
          </div>
        </div>
      </Card>

      {/* Market Orders Table */}
      <Card
        title={`My Market Orders (${data?.total || 0})`}
        actions={
          data && data.items.length > 0 ? (
            <div className="flex gap-2">
              <Tooltip content="Export market orders data as a CSV file">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => {
                    if (data?.items) {
                      downloadCSV(
                        data.items.map((order: CharacterMarketOrder) => ({
                          'Order ID': order.order_id,
                          'Item': order.type_name || `Type ${order.type_id}`,
                          'Type': order.is_buy_order ? 'Buy' : 'Sell',
                          'Price (ISK)': order.price,
                          'Volume Remaining': order.volume_remain,
                          'Volume Total': order.volume_total,
                          'Location': order.location_name || `Location ${order.location_id}`,
                          'System': order.system_name || 'Unknown',
                          'Region': order.region_name || 'Unknown',
                          'Issued': order.issued || 'N/A',
                          'Expires': order.expires || 'N/A',
                          'Active': order.is_active ? 'Yes' : 'No',
                        })),
                        'market-orders-export',
                        ['Order ID', 'Item', 'Type', 'Price (ISK)', 'Volume Remaining', 'Volume Total', 'Location', 'System', 'Region', 'Issued', 'Expires', 'Active']
                      )
                      showToast('Market orders exported to CSV', 'success')
                    }
                  }}
                >
                  Export CSV
                </Button>
              </Tooltip>
              <Tooltip content="Export market orders data as a JSON file">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => {
                    if (data?.items) {
                      downloadJSON(data.items, 'market-orders-export')
                      showToast('Market orders exported to JSON', 'success')
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
        {!characterId ? (
          <div className="text-center py-8 text-gray-400">
            Please select a character to view market orders
          </div>
        ) : isLoading ? (
          <TableSkeleton rows={10} columns={6} />
        ) : error ? (
          <div className="text-center py-8 text-red-400">Error loading market orders</div>
        ) : data && data.items.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            No market orders found. Click "Sync Orders" to fetch your orders from EVE Online.
          </div>
        ) : (
          <>
            <Table
              data={data?.items || []}
              columns={columns}
              keyExtractor={(item) => item.id.toString()}
              emptyMessage="No market orders found"
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
    </div>
  )
}
