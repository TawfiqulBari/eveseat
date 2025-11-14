import React, { useState, useMemo } from 'react'

type SortDirection = 'asc' | 'desc' | null

interface TableColumn<T> {
  key: string
  header: string
  render?: (item: T) => React.ReactNode
  className?: string
  sortable?: boolean
  sortKey?: string | ((item: T) => string | number | Date)
}

interface TableProps<T> {
  data: T[]
  columns: TableColumn<T>[]
  keyExtractor: (item: T) => string | number
  className?: string
  emptyMessage?: string
  defaultSort?: { key: string; direction: SortDirection }
  onSortChange?: (key: string, direction: SortDirection) => void
}

export function Table<T>({
  data,
  columns,
  keyExtractor,
  className = '',
  emptyMessage = 'No data available',
  defaultSort,
  onSortChange,
}: TableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(defaultSort?.key || null)
  const [sortDirection, setSortDirection] = useState<SortDirection>(defaultSort?.direction || null)

  const handleSort = (column: TableColumn<T>) => {
    if (!column.sortable) return

    const key = column.key
    let newDirection: SortDirection = 'asc'

    if (sortKey === key) {
      if (sortDirection === 'asc') {
        newDirection = 'desc'
      } else if (sortDirection === 'desc') {
        newDirection = null
      }
    }

    setSortKey(newDirection ? key : null)
    setSortDirection(newDirection)

    if (onSortChange) {
      onSortChange(key, newDirection)
    }
  }

  const sortedData = useMemo(() => {
    if (!sortKey || !sortDirection) return data

    const column = columns.find((col) => col.key === sortKey)
    if (!column || !column.sortable) return data

    return [...data].sort((a, b) => {
      let aValue: any
      let bValue: any

      if (column.sortKey) {
        if (typeof column.sortKey === 'function') {
          aValue = column.sortKey(a)
          bValue = column.sortKey(b)
        } else {
          aValue = (a as any)[column.sortKey]
          bValue = (b as any)[column.sortKey]
        }
      } else {
        aValue = (a as any)[column.key]
        bValue = (b as any)[column.key]
      }

      // Handle null/undefined values
      if (aValue == null && bValue == null) return 0
      if (aValue == null) return 1
      if (bValue == null) return -1

      // Handle dates
      if (aValue instanceof Date && bValue instanceof Date) {
        return sortDirection === 'asc'
          ? aValue.getTime() - bValue.getTime()
          : bValue.getTime() - aValue.getTime()
      }

      // Handle numbers
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortDirection === 'asc' ? aValue - bValue : bValue - aValue
      }

      // Handle strings
      const aStr = String(aValue).toLowerCase()
      const bStr = String(bValue).toLowerCase()
      if (sortDirection === 'asc') {
        return aStr.localeCompare(bStr)
      } else {
        return bStr.localeCompare(aStr)
      }
    })
  }, [data, sortKey, sortDirection, columns])

  if (data.length === 0) {
    return (
      <div className={`text-center py-8 text-gray-400 ${className}`}>
        {emptyMessage}
      </div>
    )
  }

  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="min-w-full divide-y divide-eve-gray" role="table">
        <thead className="bg-eve-dark">
          <tr>
            {columns.map((column) => {
              const isSortable = column.sortable !== false
              const isSorted = sortKey === column.key
              const isAsc = sortDirection === 'asc'
              const isDesc = sortDirection === 'desc'
              const sortLabel = isSorted 
                ? (isAsc ? 'sorted ascending' : 'sorted descending')
                : 'sortable'

              return (
                <th
                  key={column.key}
                  onClick={() => handleSort(column)}
                  onKeyDown={(e) => {
                    if (isSortable && (e.key === 'Enter' || e.key === ' ')) {
                      e.preventDefault()
                      handleSort(column)
                    }
                  }}
                  className={`px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider ${
                    isSortable ? 'cursor-pointer hover:bg-eve-gray select-none focus:outline-none focus:ring-2 focus:ring-eve-blue' : ''
                  } ${column.className || ''}`}
                  tabIndex={isSortable ? 0 : undefined}
                  role={isSortable ? 'columnheader button' : 'columnheader'}
                  aria-sort={isSorted ? (isAsc ? 'ascending' : 'descending') : 'none'}
                  aria-label={isSortable ? `${column.header}, ${sortLabel}` : column.header}
                >
                  <div className="flex items-center gap-2">
                    <span>{column.header}</span>
                    {isSortable && (
                      <span className="flex flex-col" aria-hidden="true">
                        <svg
                          className={`w-3 h-3 ${isSorted && isAsc ? 'text-eve-blue' : 'text-gray-500'}`}
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path d="M5 12l5-5 5 5H5z" />
                        </svg>
                        <svg
                          className={`w-3 h-3 -mt-1 ${isSorted && isDesc ? 'text-eve-blue' : 'text-gray-500'}`}
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path d="M5 8l5 5 5-5H5z" />
                        </svg>
                      </span>
                    )}
                  </div>
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody className="bg-eve-darker divide-y divide-eve-gray">
          {sortedData.map((item) => (
            <tr key={keyExtractor(item)} className="hover:bg-eve-dark transition-colors">
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={`px-6 py-4 whitespace-nowrap text-sm text-gray-300 ${column.className || ''}`}
                >
                  {column.render ? column.render(item) : (item as any)[column.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

