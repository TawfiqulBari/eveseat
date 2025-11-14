import { useQuery } from '@tanstack/react-query'
import api from '../services/api'

export const useKillmails = (filters?: any) => {
  return useQuery({
    queryKey: ['killmails', filters],
    queryFn: async () => {
      const { data } = await api.get('/killmails', { params: filters })
      return data
    },
  })
}

