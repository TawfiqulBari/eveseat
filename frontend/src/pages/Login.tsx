import React, { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { authService } from '../services/auth'
import { logger } from '../utils/logger'

export default function Login() {
  const [searchParams] = useSearchParams()
  const error = searchParams.get('error')

  useEffect(() => {
    // If we have a code, redirect to callback page
    const code = searchParams.get('code')
    if (code) {
      const state = searchParams.get('state')
      // Redirect to backend callback which will handle OAuth and redirect back
      const callbackUrl = `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}/auth/callback?code=${code}${state ? `&state=${state}` : ''}`
      window.location.href = callbackUrl
    }
  }, [searchParams])

  const handleLogin = async () => {
    try {
      logger.info('Initiating EVE SSO login')
      // Redirect to backend login endpoint which will redirect to EVE SSO
      window.location.href = `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}/auth/login`
    } catch (error) {
      logger.error('Login redirect failed', error)
    }
  }

  return (
    <div className="min-h-screen bg-eve-darker flex items-center justify-center">
      <div className="max-w-md w-full bg-eve-dark border border-eve-gray rounded-lg shadow-lg p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">EVE Manager</h1>
          <p className="text-gray-400">EVE Online Management Platform</p>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-900/20 border border-red-600 rounded-lg text-red-300">
            {error === 'invalid_state' && 'Invalid authentication state. Please try again.'}
            {error === 'token_error' && 'Failed to authenticate. Please try again.'}
            {!['invalid_state', 'token_error'].includes(error) && `Error: ${error}`}
          </div>
        )}

        <div className="space-y-4">
          <button
            onClick={handleLogin}
            className="w-full bg-eve-blue hover:bg-eve-blue-dark text-white font-medium py-3 px-4 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-eve-blue focus:ring-offset-2 focus:ring-offset-eve-dark"
          >
            Login with EVE Online
          </button>

          <p className="text-sm text-gray-400 text-center">
            You will be redirected to EVE Online's SSO to authenticate
          </p>
        </div>
      </div>
    </div>
  )
}

