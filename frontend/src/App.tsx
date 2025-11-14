import { lazy, Suspense, useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import { ErrorBoundary } from './components/common/ErrorBoundary'
import { Layout } from './components/Layout'
import { LoadingSpinner } from './components/common/LoadingSpinner'

// Lazy load pages for better code splitting
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Map = lazy(() => import('./pages/Map'))
const Killmails = lazy(() => import('./pages/Killmails'))
const Corporations = lazy(() => import('./pages/Corporations'))
const Market = lazy(() => import('./pages/Market'))
const Fleets = lazy(() => import('./pages/Fleets'))
const Wallet = lazy(() => import('./pages/Wallet'))
const Contracts = lazy(() => import('./pages/Contracts'))
const Contacts = lazy(() => import('./pages/Contacts'))
const Calendar = lazy(() => import('./pages/Calendar'))
const Login = lazy(() => import('./pages/Login'))
const Callback = lazy(() => import('./pages/Callback'))

function ProtectedRoutes() {
  const location = useLocation()
  const [isAuthenticated, setIsAuthenticated] = useState(() => 
    !!localStorage.getItem('access_token')
  )

  // Re-check authentication on location change (e.g., after callback)
  useEffect(() => {
    const checkAuth = () => {
      setIsAuthenticated(!!localStorage.getItem('access_token'))
    }
    
    checkAuth()
    
    // Listen for storage changes (in case localStorage is updated in another tab/window)
    window.addEventListener('storage', checkAuth)
    
    // Also check on location change
    const interval = setInterval(checkAuth, 100)
    
    return () => {
      window.removeEventListener('storage', checkAuth)
      clearInterval(interval)
    }
  }, [location])

  if (!isAuthenticated) {
    return <Login />
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/map" element={<Map />} />
        <Route path="/killmails" element={<Killmails />} />
        <Route path="/corporations" element={<Corporations />} />
        <Route path="/market" element={<Market />} />
        <Route path="/fleets" element={<Fleets />} />
        <Route path="/wallet" element={<Wallet />} />
        <Route path="/contracts" element={<Contracts />} />
        <Route path="/contacts" element={<Contacts />} />
        <Route path="/calendar" element={<Calendar />} />
      </Routes>
    </Layout>
  )
}

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Suspense
          fallback={
            <div className="flex items-center justify-center min-h-screen">
              <LoadingSpinner size="lg" />
            </div>
          }
        >
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/callback" element={<Callback />} />
            <Route path="/auth/callback" element={<Callback />} />
            <Route path="/*" element={<ProtectedRoutes />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </ErrorBoundary>
  )
}

export default App

