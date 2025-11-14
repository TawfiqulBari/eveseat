/**
 * Skills API Service
 */
import api from './api';

export interface Skill {
  id: number;
  skill_id: number;
  active_skill_level: number;
  trained_skill_level: number;
  skillpoints_in_skill: number;
}

export interface SkillQueue {
  id: number;
  skill_id: number;
  queue_position: number;
  finished_level: number;
  start_date: string | null;
  finish_date: string | null;
  training_start_sp: number | null;
  level_start_sp: number | null;
  level_end_sp: number | null;
}

export interface SkillStatistics {
  total_skills: number;
  total_sp: number;
  skills_at_level_5: number;
  skills_in_training: number;
  queue_time_remaining: number | null;
}

export const skillsService = {
  /**
   * List skills
   */
  listSkills: async (params?: {
    character_id?: number;
    min_level?: number;
    limit?: number;
    offset?: number;
  }) => {
    const response = await api.get<Skill[]>('/skills/', { params });
    return response.data;
  },

  /**
   * Get skill queue
   */
  getSkillQueue: async (characterId: number) => {
    const response = await api.get<SkillQueue[]>('/skills/queue/', {
      params: { character_id: characterId },
    });
    return response.data;
  },

  /**
   * Get skill statistics
   */
  getStatistics: async (characterId: number) => {
    const response = await api.get<SkillStatistics>(`/skills/statistics/${characterId}`);
    return response.data;
  },

  /**
   * Trigger skill sync
   */
  triggerSync: async (characterId: number) => {
    const response = await api.post(`/skills/sync/${characterId}`);
    return response.data;
  },
};
