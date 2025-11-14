import React, { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import api from '../services/api'
import { logger } from '../utils/logger'

export default function Callback() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const code = searchParams.get('code')
    const state = searchParams.get('state')
    const errorParam = searchParams.get('error')

    if (errorParam) {
      setStatus('error')
      setError(errorParam)
      setTimeout(() => navigate('/login?error=' + errorParam), 3000)
      return
    }

    // Check if this is a success redirect from backend
    const success = searchParams.get('success')
    const characterId = searchParams.get('character_id')

    if (success === 'true' && characterId) {
      // Backend has successfully authenticated, now we need to get user info
      // The backend stores tokens server-side, so we'll fetch user info
      // which will work if the backend sets a session cookie or we need to implement
      // a token endpoint that returns a temporary token for the frontend
      const handleSuccess = async () => {
        try {
          // Try to get user info - this will work if backend uses session cookies
          // or if we implement a token exchange endpoint
          const response = await api.get(`/auth/me?character_id=${characterId}`)
          
          if (response.data?.character) {
            // Store character info
            localStorage.setItem('character_id', characterId)
            localStorage.setItem('character_name', response.data.character.character_name || '')
            
            // Note: Access token is stored server-side in the backend
            // For API calls, the backend should use the server-side token
            // For now, we'll use a placeholder to indicate authentication
            localStorage.setItem('access_token', 'authenticated')
            
            setStatus('success')
            logger.info('Authentication callback successful', { characterId })
            setTimeout(() => navigate('/'), 2000)
          } else {
            throw new Error('Could not retrieve character information')
          }
        } catch (err: any) {
          logger.error('Callback error - failed to retrieve user information', err, {
            characterId,
          })
          setStatus('error')
          setError('Failed to retrieve user information. Please try logging in again.')
          setTimeout(() => navigate('/login?error=token_error'), 3000)
        }
      }
      
      handleSuccess()
      return
    }

    // If we have a code, this means EVE SSO redirected here directly
    // We should redirect to backend callback
    if (code) {
      const state = searchParams.get('state')
      const callbackUrl = `${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}/auth/callback?code=${code}${state ? `&state=${state}` : ''}`
      window.location.href = callbackUrl
      return
    }

    // No code and no success - error case
    setStatus('error')
    setError('No authorization code or success parameter received')
    setTimeout(() => navigate('/login?error=no_code'), 3000)
  }, [searchParams, navigate])

  return (
    <div className="min-h-screen bg-eve-darker flex items-center justify-center">
      <div className="max-w-md w-full bg-eve-dark border border-eve-gray rounded-lg shadow-lg p-8 text-center">
        {status === 'loading' && (
          <>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-eve-blue mx-auto mb-4"></div>
            <h2 className="text-xl font-semibold text-white mb-2">Completing authentication...</h2>
            <p className="text-gray-400">Please wait while we verify your credentials</p>
          </>
        )}
        {status === 'success' && (
          <>
            <div className="text-green-400 text-4xl mb-4">✓</div>
            <h2 className="text-xl font-semibold text-white mb-2">Authentication successful!</h2>
            <p className="text-gray-400">Redirecting to dashboard...</p>
          </>
        )}
        {status === 'error' && (
          <>
            <div className="text-red-400 text-4xl mb-4">✗</div>
            <h2 className="text-xl font-semibold text-white mb-2">Authentication failed</h2>
            <p className="text-gray-400 mb-4">{error}</p>
            <p className="text-sm text-gray-500">Redirecting to login...</p>
          </>
        )}
      </div>
    </div>
  )
}

