import api from './api'

export interface LoginResponse {
  redirect_url: string
}

export interface CallbackResponse {
  access_token: string
  character_id: number
  character_name: string
}

export interface UserInfo {
  user: {
    id: number
    username: string
    email: string
  }
  character: {
    character_id: number
    character_name: string
    corporation_id: number | null
    corporation_name: string | null
    alliance_id: number | null
    alliance_name: string | null
    security_status: number | null
  }
  token: {
    expires_at: string
    is_expired: boolean
    last_refreshed_at: string | null
  }
}

export const authService = {
  /**
   * Initiate EVE SSO login
   */
  login: async (state?: string): Promise<string> => {
    const params = state ? `?state=${state}` : ''
    const response = await api.get(`/auth/login${params}`)
    // The backend redirects, so we need to get the redirect URL from the response
    // In practice, this will be handled by redirecting the browser
    return response.request.responseURL || '/auth/login'
  },

  /**
   * Handle OAuth callback (usually handled server-side)
   */
  callback: async (code: string, state?: string): Promise<CallbackResponse> => {
    const params = new URLSearchParams({ code })
    if (state) params.append('state', state)
    const response = await api.get(`/auth/callback?${params.toString()}`)
    return response.data
  },

  /**
   * Refresh access token
   */
  refreshToken: async (characterId: number): Promise<{ access_token: string }> => {
    const response = await api.post(`/auth/refresh?character_id=${characterId}`)
    return response.data
  },

  /**
   * Get current user information
   */
  getCurrentUser: async (characterId: number): Promise<UserInfo> => {
    const response = await api.get(`/auth/me?character_id=${characterId}`)
    return response.data
  },

  /**
   * Logout (client-side only, clears tokens)
   */
  logout: (): void => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('character_id')
    localStorage.removeItem('character_name')
  },
}

