import { useQuery } from '@tanstack/react-query'
import api from '../services/api'

export const useSystems = () => {
  return useQuery({
    queryKey: ['systems'],
    queryFn: async () => {
      const { data } = await api.get('/map/systems')
      return data
    },
  })
}

