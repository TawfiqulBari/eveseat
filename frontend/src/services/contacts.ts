/**
 * Contacts API Service
 */
import api from './api';

export interface Contact {
  id: number;
  contact_id: number;
  contact_type: string;
  standing: number;
  is_watched: boolean;
  is_blocked: boolean;
  label_ids: number[];
}

export interface ContactLabel {
  id: number;
  label_id: number;
  name: string;
}

export const contactsService = {
  /**
   * List contacts for a character
   */
  listContacts: async (params?: {
    character_id?: number;
    min_standing?: number;
    max_standing?: number;
    contact_type?: string;
    watched_only?: boolean;
    limit?: number;
    offset?: number;
  }) => {
    const response = await api.get<Contact[]>('/contacts/', { params });
    return response.data;
  },

  /**
   * Get a specific contact
   */
  getContact: async (contactId: number) => {
    const response = await api.get<Contact>(`/contacts/${contactId}`);
    return response.data;
  },

  /**
   * Delete a contact
   */
  deleteContact: async (contactId: number) => {
    const response = await api.delete(`/contacts/${contactId}`);
    return response.data;
  },

  /**
   * List contact labels
   */
  listLabels: async (characterId?: number) => {
    const response = await api.get<ContactLabel[]>('/contacts/labels/', {
      params: { character_id: characterId },
    });
    return response.data;
  },

  /**
   * Trigger contact sync
   */
  triggerSync: async (characterId: number) => {
    const response = await api.post(`/contacts/sync/${characterId}`);
    return response.data;
  },
};
