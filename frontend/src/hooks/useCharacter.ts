import { useMemo } from 'react'

/**
 * Hook to get current character information from localStorage
 */
export function useCharacter() {
  return useMemo(() => {
    const characterId = localStorage.getItem('character_id')
    const characterName = localStorage.getItem('character_name')
    const accessToken = localStorage.getItem('access_token')

    return {
      characterId: characterId ? parseInt(characterId, 10) : null,
      characterName: characterName || null,
      isAuthenticated: !!accessToken && accessToken !== 'authenticated',
      hasCharacter: !!characterId,
    }
  }, [])
}

