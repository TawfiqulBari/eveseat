import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Table } from '../components/common/Table'
import { Button } from '../components/common/Button'
import { Badge } from '../components/common/Badge'
import { TableSkeleton } from '../components/common/Skeleton'
import { useToast } from '../components/common/Toast'
import { useCharacter } from '../hooks/useCharacter'
import { bookmarksService, Bookmark, BookmarkFolder } from '../services/bookmarks'
import { logger } from '../utils/logger'
import { formatDistanceToNow, format } from 'date-fns'

export default function Bookmarks() {
  const { characterId } = useCharacter()
  const queryClient = useQueryClient()
  const { showToast } = useToast()

  const [filters, setFilters] = useState({
    skip: 0,
    limit: 50,
    folder_id: undefined as number | undefined,
    location_id: undefined as number | undefined,
  })

  const [selectedBookmark, setSelectedBookmark] = useState<Bookmark | null>(null)

  const { data: folders, isLoading: foldersLoading } = useQuery({
    queryKey: ['bookmark-folders', characterId],
    queryFn: () => bookmarksService.listFolders({
      character_id: characterId || undefined,
    }),
    enabled: !!characterId,
  })

  const { data: bookmarks, isLoading: bookmarksLoading, error: bookmarksError } = useQuery({
    queryKey: ['bookmarks', characterId, filters],
    queryFn: () => bookmarksService.listBookmarks({
      character_id: characterId || undefined,
      ...filters,
      offset: filters.skip,
    }),
    enabled: !!characterId,
  })

  const { data: statistics, isLoading: statsLoading } = useQuery({
    queryKey: ['bookmark-statistics', characterId],
    queryFn: () => bookmarksService.getStatistics(characterId!),
    enabled: !!characterId,
  })

  const syncMutation = useMutation({
    mutationFn: () => bookmarksService.triggerSync(characterId!),
    onSuccess: () => {
      showToast('Bookmarks sync started', 'success')
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['bookmarks'] })
        queryClient.invalidateQueries({ queryKey: ['bookmark-folders'] })
        queryClient.invalidateQueries({ queryKey: ['bookmark-statistics'] })
      }, 2000)
    },
    onError: (error) => {
      logger.error('Failed to sync bookmarks', error)
      showToast('Failed to sync bookmarks', 'error')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (bookmarkId: number) => bookmarksService.deleteBookmark(bookmarkId),
    onSuccess: () => {
      showToast('Bookmark deleted successfully', 'success')
      queryClient.invalidateQueries({ queryKey: ['bookmarks'] })
      queryClient.invalidateQueries({ queryKey: ['bookmark-statistics'] })
      setSelectedBookmark(null)
    },
    onError: (error) => {
      logger.error('Failed to delete bookmark', error)
      showToast('Failed to delete bookmark', 'error')
    },
  })

  const getFolderName = (folderId: number | null) => {
    if (!folderId || !folders) return 'No Folder'
    const folder = folders.find(f => f.id === folderId)
    return folder?.name || `Folder ${folderId}`
  }

  const columns = [
    {
      key: 'created',
      header: 'Created',
      sortable: true,
      sortKey: (bookmark: Bookmark) => new Date(bookmark.created),
      render: (bookmark: Bookmark) => (
        <div>
          <div className="text-white text-sm">
            {format(new Date(bookmark.created), 'MMM dd, yyyy')}
          </div>
          <div className="text-xs text-gray-400">
            {formatDistanceToNow(new Date(bookmark.created), { addSuffix: true })}
          </div>
        </div>
      ),
    },
    {
      key: 'label',
      header: 'Label',
      sortable: true,
      sortKey: (bookmark: Bookmark) => bookmark.label,
      render: (bookmark: Bookmark) => (
        <div>
          <div className="text-white font-medium">{bookmark.label}</div>
          {bookmark.notes && (
            <div className="text-xs text-gray-400 mt-1 line-clamp-1">{bookmark.notes}</div>
          )}
        </div>
      ),
    },
    {
      key: 'location',
      header: 'Location',
      sortable: true,
      sortKey: (bookmark: Bookmark) => bookmark.location_id,
      render: (bookmark: Bookmark) => (
        <span className="text-gray-300">Location {bookmark.location_id}</span>
      ),
    },
    {
      key: 'folder',
      header: 'Folder',
      sortable: true,
      sortKey: (bookmark: Bookmark) => getFolderName(bookmark.folder_id),
      render: (bookmark: Bookmark) => (
        <Badge variant={bookmark.folder_id ? 'info' : 'secondary'}>
          {getFolderName(bookmark.folder_id)}
        </Badge>
      ),
    },
    {
      key: 'coordinates',
      header: 'Coordinates',
      sortable: false,
      render: (bookmark: Bookmark) => (
        bookmark.coordinates ? (
          <span className="text-xs text-gray-400 font-mono">
            x: {bookmark.coordinates.x?.toFixed(0) || 'N/A'},
            y: {bookmark.coordinates.y?.toFixed(0) || 'N/A'},
            z: {bookmark.coordinates.z?.toFixed(0) || 'N/A'}
          </span>
        ) : (
          <span className="text-gray-500">-</span>
        )
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      sortable: false,
      render: (bookmark: Bookmark) => (
        <div className="flex gap-2">
          <Button
            onClick={() => setSelectedBookmark(bookmark)}
            variant="secondary"
            size="sm"
          >
            View
          </Button>
          <Button
            onClick={() => deleteMutation.mutate(bookmark.id)}
            variant="danger"
            size="sm"
            disabled={deleteMutation.isPending}
          >
            Delete
          </Button>
        </div>
      ),
    },
  ]

  if (!characterId) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Bookmarks</h1>
          <p className="text-gray-400">Please select a character</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Bookmarks</h1>
          <p className="text-gray-400">Manage your location bookmarks</p>
        </div>
        <Button
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
        >
          {syncMutation.isPending ? 'Syncing...' : 'Sync Bookmarks'}
        </Button>
      </div>

      {/* Statistics */}
      {statsLoading ? (
        <Card title="Bookmark Statistics">
          <div className="text-gray-400">Loading statistics...</div>
        </Card>
      ) : statistics ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card title="Total Bookmarks">
            <div className="text-3xl font-bold text-white">{statistics.total_bookmarks}</div>
          </Card>
          <Card title="Total Folders">
            <div className="text-3xl font-bold text-blue-400">{statistics.total_folders}</div>
          </Card>
          <Card title="Avg per Folder">
            <div className="text-3xl font-bold text-green-400">
              {statistics.total_folders > 0
                ? (statistics.total_bookmarks / statistics.total_folders).toFixed(1)
                : '0'}
            </div>
          </Card>
        </div>
      ) : null}

      {/* Bookmarks by Folder */}
      {statistics && Object.keys(statistics.bookmarks_by_folder).length > 0 && (
        <Card title="Bookmarks by Folder">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Object.entries(statistics.bookmarks_by_folder).map(([folderName, count]) => (
              <div key={folderName} className="p-4 bg-eve-darker rounded-lg">
                <div className="text-white font-medium">{folderName}</div>
                <div className="text-2xl text-blue-400 mt-2">{count} bookmarks</div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Folders List */}
      {foldersLoading ? (
        <Card title="Folders">
          <div className="text-gray-400">Loading folders...</div>
        </Card>
      ) : folders && folders.length > 0 ? (
        <Card title="Folders">
          <div className="flex flex-wrap gap-2">
            {folders.map((folder) => (
              <Badge
                key={folder.id}
                variant={filters.folder_id === folder.id ? 'info' : 'secondary'}
                className="cursor-pointer"
                onClick={() => setFilters({
                  ...filters,
                  folder_id: filters.folder_id === folder.id ? undefined : folder.id,
                })}
              >
                {folder.name}
              </Badge>
            ))}
            {filters.folder_id && (
              <Badge
                variant="danger"
                className="cursor-pointer"
                onClick={() => setFilters({ ...filters, folder_id: undefined })}
              >
                Clear Filter
              </Badge>
            )}
          </div>
        </Card>
      ) : null}

      {/* Filters */}
      <Card title="Filters">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Location ID
            </label>
            <input
              type="number"
              value={filters.location_id || ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  location_id: e.target.value ? parseInt(e.target.value) : undefined,
                })
              }
              className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
              placeholder="Filter by location..."
            />
          </div>
        </div>
      </Card>

      {/* Bookmarks Table */}
      <Card title={`Bookmarks (${bookmarks?.length || 0})`}>
        {bookmarksLoading ? (
          <TableSkeleton rows={10} columns={6} />
        ) : bookmarksError ? (
          <div className="text-center py-8 text-red-400">
            Error loading bookmarks. Try syncing your bookmarks.
          </div>
        ) : (
          <Table
            data={bookmarks || []}
            columns={columns}
            keyExtractor={(item) => item.id.toString()}
            emptyMessage="No bookmarks found. Click 'Sync Bookmarks' to fetch from EVE Online."
            defaultSort={{ key: 'created', direction: 'desc' }}
          />
        )}
      </Card>

      {/* Bookmark Details Modal */}
      {selectedBookmark && (
        <Card title={`Bookmark: ${selectedBookmark.label}`}>
          <div className="space-y-4">
            <div>
              <div className="text-sm text-gray-400">Location</div>
              <div className="text-white">Location {selectedBookmark.location_id}</div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Folder</div>
              <div className="text-white">{getFolderName(selectedBookmark.folder_id)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Created</div>
              <div className="text-white">
                {format(new Date(selectedBookmark.created), 'PPpp')}
              </div>
            </div>
            {selectedBookmark.notes && (
              <div>
                <div className="text-sm text-gray-400">Notes</div>
                <div className="text-white whitespace-pre-wrap">{selectedBookmark.notes}</div>
              </div>
            )}
            {selectedBookmark.coordinates && (
              <div>
                <div className="text-sm text-gray-400">Coordinates</div>
                <div className="text-white font-mono text-sm">
                  X: {selectedBookmark.coordinates.x?.toFixed(2) || 'N/A'}<br/>
                  Y: {selectedBookmark.coordinates.y?.toFixed(2) || 'N/A'}<br/>
                  Z: {selectedBookmark.coordinates.z?.toFixed(2) || 'N/A'}
                </div>
              </div>
            )}
            <div className="flex gap-2">
              <Button
                onClick={() => setSelectedBookmark(null)}
                variant="secondary"
                fullWidth
              >
                Close
              </Button>
              <Button
                onClick={() => deleteMutation.mutate(selectedBookmark.id)}
                variant="danger"
                fullWidth
                disabled={deleteMutation.isPending}
              >
                Delete Bookmark
              </Button>
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}
