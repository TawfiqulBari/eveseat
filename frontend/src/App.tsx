import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
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
const Login = lazy(() => import('./pages/Login'))
const Callback = lazy(() => import('./pages/Callback'))

function App() {
  // Check if user is authenticated
  const isAuthenticated = !!localStorage.getItem('access_token')

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
            <Route
              path="/*"
              element={
                isAuthenticated ? (
                  <Layout>
                    <Routes>
                      <Route path="/" element={<Dashboard />} />
                      <Route path="/map" element={<Map />} />
                      <Route path="/killmails" element={<Killmails />} />
                      <Route path="/corporations" element={<Corporations />} />
                      <Route path="/market" element={<Market />} />
                      <Route path="/fleets" element={<Fleets />} />
                    </Routes>
                  </Layout>
                ) : (
                  <Login />
                )
              }
            />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </ErrorBoundary>
  )
}

export default App

