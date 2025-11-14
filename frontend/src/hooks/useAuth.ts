import { useAuthStore } from '../store/authStore'

export const useAuth = () => {
  const { isAuthenticated, user, setUser, logout } = useAuthStore()
  return { isAuthenticated, user, setUser, logout }
}

