import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Table } from '../components/common/Table'
import { Button } from '../components/common/Button'
import { Pagination } from '../components/common/Pagination'
import { TableSkeleton } from '../components/common/Skeleton'
import { Tooltip } from '../components/common/Tooltip'
import { useToast } from '../components/common/Toast'
import { formatISK } from '../utils/formatters'
import { downloadCSV, downloadJSON } from '../utils/export'
import { marketService, MarketOrder, ListResponse } from '../services/market'

export default function Market() {
  const { showToast } = useToast()
  const [filters, setFilters] = useState({
    region_id: undefined as number | undefined,
    system_id: undefined as number | undefined,
    type_id: undefined as number | undefined,
    is_buy_order: undefined as boolean | undefined,
    skip: 0,
    limit: 50,
  })

  const { data, isLoading, error, refetch } = useQuery<ListResponse<MarketOrder>>({
    queryKey: ['market-orders', filters],
    queryFn: () => marketService.getOrders(filters),
    onError: (err: any) => {
      showToast(err.response?.data?.detail || 'Failed to load market orders', 'error')
    },
  })

  const columns = [
    {
      key: 'type_name',
      header: 'Item',
      sortable: true,
      sortKey: (order: MarketOrder) => order.type_name || `Type ${order.type_id}`,
      render: (order: MarketOrder) => (
        <span className="text-white font-medium">{order.type_name || `Type ${order.type_id}`}</span>
      ),
    },
    {
      key: 'location',
      header: 'Location',
      sortable: true,
      sortKey: (order: MarketOrder) => order.location_name || `Location ${order.location_id}`,
      render: (order: MarketOrder) => (
        <div>
          <div className="text-white">{order.location_name || `Location ${order.location_id}`}</div>
          {order.system_name && (
            <div className="text-sm text-gray-400">{order.system_name}</div>
          )}
        </div>
      ),
    },
    {
      key: 'price',
      header: 'Price',
      sortable: true,
      sortKey: (order: MarketOrder) => order.price,
      render: (order: MarketOrder) => (
        <span className="text-yellow-400 font-medium">
          {formatISK(order.price)}
        </span>
      ),
    },
    {
      key: 'volume',
      header: 'Volume',
      sortable: true,
      sortKey: (order: MarketOrder) => order.volume_remain,
      render: (order: MarketOrder) => (
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
      sortKey: (order: MarketOrder) => order.is_buy_order ? 'Buy' : 'Sell',
      render: (order: MarketOrder) => (
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
      sortKey: (order: MarketOrder) => order.expires ? new Date(order.expires) : new Date(0),
      render: (order: MarketOrder) => (
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
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Region ID
            </label>
            <input
              type="number"
              value={filters.region_id || ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  region_id: e.target.value ? parseInt(e.target.value, 10) : undefined,
                })
              }
              className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
              placeholder="Region ID"
            />
          </div>
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
              Type ID
            </label>
            <input
              type="number"
              value={filters.type_id || ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  type_id: e.target.value ? parseInt(e.target.value, 10) : undefined,
                })
              }
              className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
              placeholder="Item Type ID"
            />
          </div>
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
          <div className="flex items-end">
            <Button onClick={() => refetch()} className="w-full">
              Apply Filters
            </Button>
          </div>
        </div>
      </Card>

      {/* Market Orders Table */}
      <Card
        title={`Market Orders (${data?.total || 0})`}
        actions={
          data && data.items.length > 0 ? (
            <div className="flex gap-2">
              <Tooltip content="Export market orders data as a CSV file">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => {
                    const marketData = data as ListResponse<MarketOrder> | undefined
                    if (marketData?.items) {
                      downloadCSV(
                        marketData.items.map((order: MarketOrder) => ({
                          'Order ID': order.order_id,
                          'Item': order.type_name || `Type ${order.type_id}`,
                          'Type': order.is_buy_order ? 'Buy' : 'Sell',
                          'Price (ISK)': order.price,
                          'Volume Remaining': order.volume_remain,
                          'Volume Total': order.volume_total,
                          'Location': order.location_name || `Location ${order.location_id}`,
                          'System': order.system_name || 'Unknown',
                          'Issued': order.issued,
                          'Expires': order.expires || 'N/A',
                        })),
                        'market-orders-export',
                        ['Order ID', 'Item', 'Type', 'Price (ISK)', 'Volume Remaining', 'Volume Total', 'Location', 'System', 'Issued', 'Expires']
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
                    const marketData = data as ListResponse<MarketOrder> | undefined
                    if (marketData?.items) {
                      downloadJSON(marketData.items, 'market-orders-export')
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
        {isLoading ? (
          <TableSkeleton rows={10} columns={6} />
        ) : error ? (
          <div className="text-center py-8 text-red-400">Error loading market orders</div>
        ) : (
          <>
            <Table
              data={(data as ListResponse<MarketOrder> | undefined)?.items || []}
              columns={columns}
              keyExtractor={(item) => item.id.toString()}
              emptyMessage="No market orders found"
            />
            {(() => {
              const marketData = data as ListResponse<MarketOrder> | undefined
              return marketData && marketData.total > 0 && (
              <div className="mt-4">
                <Pagination
                  currentPage={Math.floor(filters.skip / filters.limit) + 1}
                  totalPages={Math.ceil(marketData.total / filters.limit)}
                  totalItems={marketData.total}
                  pageSize={filters.limit}
                  onPageChange={(page) => setFilters({ ...filters, skip: (page - 1) * filters.limit })}
                  onPageSizeChange={(size) => setFilters({ ...filters, limit: size, skip: 0 })}
                />
              </div>
            )
            })()}
          </>
        )}
      </Card>
    </div>
  )
}
