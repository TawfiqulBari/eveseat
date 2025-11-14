/**
 * Calendar API Service
 */
import api from './api';

export interface CalendarEvent {
  id: number;
  event_id: number;
  title: string;
  description: string | null;
  event_date: string;
  duration: number;
  importance: number;
  owner_id: number;
  owner_name: string;
  owner_type: string;
  response: string | null;
}

export interface CalendarEventAttendee {
  id: number;
  character_id: number;
  event_response: string;
}

export const calendarService = {
  /**
   * List calendar events
   */
  listEvents: async (params?: {
    character_id?: number;
    from_date?: string;
    to_date?: string;
    response_filter?: string;
    limit?: number;
    offset?: number;
  }) => {
    const response = await api.get<CalendarEvent[]>('/calendar/', { params });
    return response.data;
  },

  /**
   * Get a specific event
   */
  getEvent: async (eventId: number) => {
    const response = await api.get<CalendarEvent>(`/calendar/${eventId}`);
    return response.data;
  },

  /**
   * Get event attendees
   */
  getEventAttendees: async (eventId: number) => {
    const response = await api.get<CalendarEventAttendee[]>(`/calendar/${eventId}/attendees`);
    return response.data;
  },

  /**
   * Respond to an event
   */
  respondToEvent: async (eventId: number, characterId: number, response: string) => {
    const apiResponse = await api.put(`/calendar/${eventId}/respond`, {
      character_id: characterId,
      response,
    });
    return apiResponse.data;
  },

  /**
   * Get upcoming events
   */
  getUpcomingEvents: async (characterId?: number, days: number = 7) => {
    const response = await api.get<CalendarEvent[]>('/calendar/upcoming/', {
      params: { character_id: characterId, days },
    });
    return response.data;
  },

  /**
   * Trigger calendar sync
   */
  triggerSync: async (characterId: number) => {
    const response = await api.post(`/calendar/sync/${characterId}`);
    return response.data;
  },
};
