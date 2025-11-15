import axios from 'axios'
import { logger } from '../utils/logger'

// Use environment variable or construct from current location
const API_URL = import.meta.env.VITE_API_URL ||
  (typeof window !== 'undefined' ? `${window.location.protocol}//${window.location.host}/api/v1` : '/api/v1')

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for adding auth tokens
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    const characterId = localStorage.getItem('character_id')
    
    // If we have a character ID, add it as a query parameter for endpoints that need it
    // The backend will use server-side stored tokens for that character
    if (characterId && !config.params) {
      config.params = {}
    }
    if (characterId && config.url && !config.url.includes('character_id=')) {
      // Only add character_id to endpoints that might need it
      // Some endpoints get character_id from the token, others need it as a param
      const needsCharacterId = ['/auth/me', '/fleets'].some(path => config.url?.includes(path))
      if (needsCharacterId) {
        config.params = { ...config.params, character_id: characterId }
      }
    }
    
    // If we have a token (not just 'authenticated' placeholder), use it
    if (token && token !== 'authenticated') {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for handling errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized - redirect to login
      logger.warn('Unauthorized request, redirecting to login', {
        url: error.config?.url,
      })
      localStorage.removeItem('access_token')
      localStorage.removeItem('character_id')
      window.location.href = '/login'
    } else if (error.response) {
      // Log API errors
      logger.error('API request failed', error, {
        url: error.config?.url,
        method: error.config?.method,
        status: error.response.status,
        statusText: error.response.statusText,
      })
    } else if (error.request) {
      // Network error
      logger.error('Network error - no response received', error, {
        url: error.config?.url,
      })
    } else {
      // Request setup error
      logger.error('Request setup error', error)
    }
    return Promise.reject(error)
  }
)

export default api

