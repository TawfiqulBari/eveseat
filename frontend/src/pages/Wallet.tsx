import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Table } from '../components/common/Table'
import { Button } from '../components/common/Button'
import { Badge } from '../components/common/Badge'
import { TableSkeleton } from '../components/common/Skeleton'
import { useToast } from '../components/common/Toast'
import { useCharacter } from '../hooks/useCharacter'
import { walletService, WalletJournalEntry, WalletTransaction, WalletStatistics } from '../services/wallet'
import { logger } from '../utils/logger'
import { formatISK } from '../utils/formatters'
import { formatDistanceToNow, format } from 'date-fns'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts'

export default function Wallet() {
  const { characterId } = useCharacter()
  const queryClient = useQueryClient()
  const { showToast } = useToast()

  const [activeTab, setActiveTab] = useState<'journal' | 'transactions'>('journal')
  const [journalFilters, setJournalFilters] = useState({
    skip: 0,
    limit: 50,
    from_date: undefined as string | undefined,
    to_date: undefined as string | undefined,
    ref_type: undefined as string | undefined,
  })

  const [transactionFilters, setTransactionFilters] = useState({
    skip: 0,
    limit: 50,
    from_date: undefined as string | undefined,
    to_date: undefined as string | undefined,
    type_id: undefined as number | undefined,
    is_buy: undefined as boolean | undefined,
  })

  const { data: balance, isLoading: balanceLoading } = useQuery({
    queryKey: ['wallet-balance', characterId],
    queryFn: () => walletService.getBalance(characterId!),
    enabled: !!characterId,
  })

  const { data: statistics, isLoading: statsLoading } = useQuery({
    queryKey: ['wallet-statistics', characterId],
    queryFn: () => walletService.getStatistics(characterId!, 30),
    enabled: !!characterId,
  })

  const { data: journal, isLoading: journalLoading, error: journalError } = useQuery({
    queryKey: ['wallet-journal', characterId, journalFilters],
    queryFn: () => walletService.listJournal({
      character_id: characterId || undefined,
      ...journalFilters,
      offset: journalFilters.skip,
    }),
    enabled: !!characterId && activeTab === 'journal',
  })

  const { data: transactions, isLoading: transactionsLoading, error: transactionsError } = useQuery({
    queryKey: ['wallet-transactions', characterId, transactionFilters],
    queryFn: () => walletService.listTransactions({
      character_id: characterId || undefined,
      ...transactionFilters,
      offset: transactionFilters.skip,
    }),
    enabled: !!characterId && activeTab === 'transactions',
  })

  const syncMutation = useMutation({
    mutationFn: () => walletService.triggerSync(characterId!),
    onSuccess: () => {
      showToast('Wallet sync started', 'success')
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['wallet-balance'] })
        queryClient.invalidateQueries({ queryKey: ['wallet-statistics'] })
        queryClient.invalidateQueries({ queryKey: ['wallet-journal'] })
        queryClient.invalidateQueries({ queryKey: ['wallet-transactions'] })
      }, 2000)
    },
    onError: (error) => {
      logger.error('Failed to sync wallet', error)
      showToast('Failed to sync wallet', 'error')
    },
  })

  const journalColumns = [
    {
      key: 'date',
      header: 'Date',
      sortable: true,
      sortKey: (entry: WalletJournalEntry) => new Date(entry.date),
      render: (entry: WalletJournalEntry) => (
        <div>
          <div className="text-white text-sm">
            {format(new Date(entry.date), 'MMM dd, yyyy HH:mm')}
          </div>
          <div className="text-xs text-gray-400">
            {formatDistanceToNow(new Date(entry.date), { addSuffix: true })}
          </div>
        </div>
      ),
    },
    {
      key: 'ref_type',
      header: 'Type',
      sortable: true,
      sortKey: (entry: WalletJournalEntry) => entry.ref_type,
      render: (entry: WalletJournalEntry) => (
        <Badge variant="secondary">{entry.ref_type}</Badge>
      ),
    },
    {
      key: 'description',
      header: 'Description',
      sortable: false,
      render: (entry: WalletJournalEntry) => (
        <span className="text-gray-300">{entry.description}</span>
      ),
    },
    {
      key: 'amount',
      header: 'Amount',
      sortable: true,
      sortKey: (entry: WalletJournalEntry) => entry.amount,
      render: (entry: WalletJournalEntry) => (
        <span className={entry.amount >= 0 ? 'text-green-400 font-medium' : 'text-red-400 font-medium'}>
          {entry.amount >= 0 ? '+' : ''}{formatISK(entry.amount)}
        </span>
      ),
    },
    {
      key: 'balance',
      header: 'Balance',
      sortable: true,
      sortKey: (entry: WalletJournalEntry) => entry.balance || 0,
      render: (entry: WalletJournalEntry) => (
        entry.balance !== null ? (
          <span className="text-yellow-400 font-medium">{formatISK(entry.balance)}</span>
        ) : (
          <span className="text-gray-500">-</span>
        )
      ),
    },
  ]

  const transactionColumns = [
    {
      key: 'date',
      header: 'Date',
      sortable: true,
      sortKey: (tx: WalletTransaction) => new Date(tx.date),
      render: (tx: WalletTransaction) => (
        <div>
          <div className="text-white text-sm">
            {format(new Date(tx.date), 'MMM dd, yyyy HH:mm')}
          </div>
          <div className="text-xs text-gray-400">
            {formatDistanceToNow(new Date(tx.date), { addSuffix: true })}
          </div>
        </div>
      ),
    },
    {
      key: 'type',
      header: 'Type',
      sortable: true,
      sortKey: (tx: WalletTransaction) => tx.is_buy ? 'buy' : 'sell',
      render: (tx: WalletTransaction) => (
        <Badge variant={tx.is_buy ? 'success' : 'warning'}>
          {tx.is_buy ? 'Buy' : 'Sell'}
        </Badge>
      ),
    },
    {
      key: 'type_id',
      header: 'Item',
      sortable: true,
      sortKey: (tx: WalletTransaction) => tx.type_id,
      render: (tx: WalletTransaction) => (
        <span className="text-white">Type {tx.type_id}</span>
      ),
    },
    {
      key: 'quantity',
      header: 'Quantity',
      sortable: true,
      sortKey: (tx: WalletTransaction) => tx.quantity,
      render: (tx: WalletTransaction) => (
        <span className="text-gray-300">{tx.quantity.toLocaleString()}</span>
      ),
    },
    {
      key: 'unit_price',
      header: 'Unit Price',
      sortable: true,
      sortKey: (tx: WalletTransaction) => tx.unit_price,
      render: (tx: WalletTransaction) => (
        <span className="text-yellow-400">{formatISK(tx.unit_price)}</span>
      ),
    },
    {
      key: 'total',
      header: 'Total',
      sortable: true,
      sortKey: (tx: WalletTransaction) => tx.quantity * tx.unit_price,
      render: (tx: WalletTransaction) => (
        <span className="text-yellow-400 font-medium">
          {formatISK(tx.quantity * tx.unit_price)}
        </span>
      ),
    },
    {
      key: 'location',
      header: 'Location',
      sortable: true,
      sortKey: (tx: WalletTransaction) => tx.location_id,
      render: (tx: WalletTransaction) => (
        <span className="text-gray-300">Location {tx.location_id}</span>
      ),
    },
  ]

  if (!characterId) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Wallet</h1>
          <p className="text-gray-400">Please select a character</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Wallet</h1>
          <p className="text-gray-400">Track your character's wallet and transactions</p>
        </div>
        <Button
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
        >
          {syncMutation.isPending ? 'Syncing...' : 'Sync Wallet'}
        </Button>
      </div>

      {/* Balance & Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card title="Current Balance">
          {balanceLoading ? (
            <div className="text-gray-400">Loading...</div>
          ) : balance !== undefined ? (
            <div className="text-3xl font-bold text-yellow-400">{formatISK(balance)}</div>
          ) : (
            <div className="text-gray-400">No data</div>
          )}
        </Card>

        {statsLoading ? (
          <>
            <Card title="Total Income"><div className="text-gray-400">Loading...</div></Card>
            <Card title="Total Expenses"><div className="text-gray-400">Loading...</div></Card>
            <Card title="Net Change"><div className="text-gray-400">Loading...</div></Card>
          </>
        ) : statistics ? (
          <>
            <Card title="Total Income (30d)">
              <div className="text-3xl font-bold text-green-400">
                {formatISK(statistics.total_income)}
              </div>
            </Card>
            <Card title="Total Expenses (30d)">
              <div className="text-3xl font-bold text-red-400">
                {formatISK(statistics.total_expenses)}
              </div>
            </Card>
            <Card title="Net Change (30d)">
              <div className={`text-3xl font-bold ${statistics.net_change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {statistics.net_change >= 0 ? '+' : ''}{formatISK(statistics.net_change)}
              </div>
            </Card>
          </>
        ) : null}
      </div>

      {/* Market Statistics */}
      {statistics && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card title="Market Buys (30d)">
            <div className="text-2xl font-bold text-white">
              {statistics.market_buys?.toLocaleString() || 0}
            </div>
          </Card>
          <Card title="Market Sells (30d)">
            <div className="text-2xl font-bold text-white">
              {statistics.market_sells?.toLocaleString() || 0}
            </div>
          </Card>
          <Card title="Market Profit (30d)">
            <div className={`text-2xl font-bold ${(statistics.market_profit || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {(statistics.market_profit || 0) >= 0 ? '+' : ''}{formatISK(statistics.market_profit || 0)}
            </div>
          </Card>
        </div>
      )}

      {/* Tabs */}
      <Card>
        <div className="flex gap-4 border-b border-eve-gray pb-4">
          <button
            onClick={() => setActiveTab('journal')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'journal'
                ? 'bg-eve-blue text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Journal
          </button>
          <button
            onClick={() => setActiveTab('transactions')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'transactions'
                ? 'bg-eve-blue text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Transactions
          </button>
        </div>

        {/* Journal Tab */}
        {activeTab === 'journal' && (
          <div className="mt-6 space-y-4">
            {/* Journal Filters */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  From Date
                </label>
                <input
                  type="date"
                  value={journalFilters.from_date || ''}
                  onChange={(e) =>
                    setJournalFilters({
                      ...journalFilters,
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
                  value={journalFilters.to_date || ''}
                  onChange={(e) =>
                    setJournalFilters({
                      ...journalFilters,
                      to_date: e.target.value || undefined,
                    })
                  }
                  className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Reference Type
                </label>
                <input
                  type="text"
                  value={journalFilters.ref_type || ''}
                  onChange={(e) =>
                    setJournalFilters({
                      ...journalFilters,
                      ref_type: e.target.value || undefined,
                    })
                  }
                  className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
                  placeholder="e.g., bounty_prizes"
                />
              </div>
            </div>

            {/* Journal Table */}
            {journalLoading ? (
              <TableSkeleton rows={10} columns={5} />
            ) : journalError ? (
              <div className="text-center py-8 text-red-400">
                Error loading wallet journal. Try syncing your wallet.
              </div>
            ) : (
              <Table
                data={journal || []}
                columns={journalColumns}
                keyExtractor={(item) => item.id.toString()}
                emptyMessage="No journal entries found. Click 'Sync Wallet' to fetch from EVE Online."
                defaultSort={{ key: 'date', direction: 'desc' }}
              />
            )}
          </div>
        )}

        {/* Transactions Tab */}
        {activeTab === 'transactions' && (
          <div className="mt-6 space-y-4">
            {/* Transaction Filters */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  From Date
                </label>
                <input
                  type="date"
                  value={transactionFilters.from_date || ''}
                  onChange={(e) =>
                    setTransactionFilters({
                      ...transactionFilters,
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
                  value={transactionFilters.to_date || ''}
                  onChange={(e) =>
                    setTransactionFilters({
                      ...transactionFilters,
                      to_date: e.target.value || undefined,
                    })
                  }
                  className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Type ID
                </label>
                <input
                  type="number"
                  value={transactionFilters.type_id || ''}
                  onChange={(e) =>
                    setTransactionFilters({
                      ...transactionFilters,
                      type_id: e.target.value ? parseInt(e.target.value) : undefined,
                    })
                  }
                  className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
                  placeholder="Item Type ID"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Transaction Type
                </label>
                <select
                  value={transactionFilters.is_buy === undefined ? '' : transactionFilters.is_buy ? 'buy' : 'sell'}
                  onChange={(e) =>
                    setTransactionFilters({
                      ...transactionFilters,
                      is_buy: e.target.value === '' ? undefined : e.target.value === 'buy',
                    })
                  }
                  className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
                >
                  <option value="">All</option>
                  <option value="buy">Buy</option>
                  <option value="sell">Sell</option>
                </select>
              </div>
            </div>

            {/* Transactions Table */}
            {transactionsLoading ? (
              <TableSkeleton rows={10} columns={7} />
            ) : transactionsError ? (
              <div className="text-center py-8 text-red-400">
                Error loading transactions. Try syncing your wallet.
              </div>
            ) : (
              <Table
                data={transactions || []}
                columns={transactionColumns}
                keyExtractor={(item) => item.id.toString()}
                emptyMessage="No transactions found. Click 'Sync Wallet' to fetch from EVE Online."
                defaultSort={{ key: 'date', direction: 'desc' }}
              />
            )}
          </div>
        )}
      </Card>
    </div>
  )
}
