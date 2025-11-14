/**
 * Bookmarks API Service
 */
import api from './api';

export interface BookmarkFolder {
  id: number;
  folder_id: number;
  name: string;
}

export interface Bookmark {
  id: number;
  bookmark_id: number;
  label: string;
  notes: string | null;
  created: string;
  location_id: number;
  creator_id: number | null;
  folder_id: number | null;
  coordinates: {
    x?: number;
    y?: number;
    z?: number;
  } | null;
  item_id: number | null;
  item_type_id: number | null;
}

export interface BookmarkStatistics {
  total_bookmarks: number;
  total_folders: number;
  bookmarks_by_folder: Record<string, number>;
}

export const bookmarksService = {
  /**
   * List bookmark folders
   */
  listFolders: async (params?: {
    character_id?: number;
  }) => {
    const response = await api.get<BookmarkFolder[]>('/bookmarks/folders/', { params });
    return response.data;
  },

  /**
   * List bookmarks
   */
  listBookmarks: async (params?: {
    character_id?: number;
    folder_id?: number;
    location_id?: number;
    limit?: number;
    offset?: number;
  }) => {
    const response = await api.get<Bookmark[]>('/bookmarks/', { params });
    return response.data;
  },

  /**
   * Get a specific bookmark
   */
  getBookmark: async (bookmarkId: number) => {
    const response = await api.get<Bookmark>(`/bookmarks/${bookmarkId}`);
    return response.data;
  },

  /**
   * Delete a bookmark
   */
  deleteBookmark: async (bookmarkId: number) => {
    const response = await api.delete(`/bookmarks/${bookmarkId}`);
    return response.data;
  },

  /**
   * Get bookmark statistics
   */
  getStatistics: async (characterId: number) => {
    const response = await api.get<BookmarkStatistics>(`/bookmarks/statistics/${characterId}`);
    return response.data;
  },

  /**
   * Trigger bookmark sync
   */
  triggerSync: async (characterId: number) => {
    const response = await api.post(`/bookmarks/sync/${characterId}`);
    return response.data;
  },
};
