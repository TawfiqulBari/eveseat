import React, { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Button } from '../components/common/Button'
import { Input } from '../components/common/Input'
import { SearchInput } from '../components/common/SearchInput'
import { CardSkeleton } from '../components/common/Skeleton'
import { Tooltip } from '../components/common/Tooltip'
import { useToast } from '../components/common/Toast'
import { useKeyboardShortcut } from '../hooks/useKeyboardShortcut'
import { logger } from '../utils/logger'
import { validateSystemId } from '../utils/validation'
import { formatDuration, formatSecurityStatus } from '../utils/formatters'
import { mapService, System } from '../services/map'
import { routesService, RouteRequest } from '../services/routes'

export default function Map() {
  const { showToast } = useToast()
  const [startSystem, setStartSystem] = useState<string>('')
  const [endSystem, setEndSystem] = useState<string>('')
  const [route, setRoute] = useState<any>(null)
  const [isCalculating, setIsCalculating] = useState(false)

  const { data: systems, isLoading: systemsLoading } = useQuery({
    queryKey: ['systems'],
    queryFn: () => mapService.getSystems({ limit: 1000 }),
  })

  // Prepare system suggestions for search
  const systemSuggestions = useMemo(() => {
    if (!systems) return []
    return systems.map((system) => ({
      id: system.system_id,
      label: `${system.system_name} (${system.system_id})`,
      value: system.system_id,
    }))
  }, [systems])

  const handleCalculateRoute = async () => {
    if (!startSystem || !endSystem) {
      showToast('Please enter both start and end system IDs', 'warning')
      return
    }

    // Validate system IDs
    const startValidation = validateSystemId(startSystem)
    const endValidation = validateSystemId(endSystem)

    if (!startValidation.isValid) {
      showToast(startValidation.error || 'Invalid start system ID', 'error')
      return
    }

    if (!endValidation.isValid) {
      showToast(endValidation.error || 'Invalid end system ID', 'error')
      return
    }

    const startId = parseInt(startSystem, 10)
    const endId = parseInt(endSystem, 10)

    setIsCalculating(true)
    try {
      const request: RouteRequest = {
        start_system_id: startId,
        end_system_id: endId,
        prefer_safer: true,
      }
      const result = await routesService.calculate(request)
      setRoute(result)
      showToast(`Route calculated: ${result.total_jumps} jumps`, 'success')
      logger.info('Route calculated successfully', { startId, endId, jumps: result.total_jumps })
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to calculate route'
      logger.error('Route calculation failed', error, { startId, endId })
      showToast(errorMessage, 'error')
      setRoute(null)
    } finally {
      setIsCalculating(false)
    }
  }

  // Keyboard shortcut: Ctrl/Cmd + Enter to calculate route
  useKeyboardShortcut('Enter', () => {
    if (startSystem && endSystem) {
      handleCalculateRoute()
    }
  }, {
    ctrlKey: true,
    preventDefault: true,
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Universe Map</h1>
        <p className="text-gray-400">Explore the EVE universe and plan routes</p>
      </div>

      {/* Route Planning */}
      <Card title="Route Planner">
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <SearchInput
                label="Start System"
                value={startSystem}
                onChange={(e) => setStartSystem(e.target.value)}
                onSelect={(item) => {
                  setStartSystem(item.value?.toString() || '')
                }}
                suggestions={systemSuggestions}
                isLoading={systemsLoading}
                placeholder="Search or enter system ID (e.g., Jita)"
              />
            </div>
            <div>
              <SearchInput
                label="End System"
                value={endSystem}
                onChange={(e) => setEndSystem(e.target.value)}
                onSelect={(item) => {
                  setEndSystem(item.value?.toString() || '')
                }}
                suggestions={systemSuggestions}
                isLoading={systemsLoading}
                placeholder="Search or enter system ID (e.g., Amarr)"
              />
            </div>
            <div className="flex items-end">
              <Tooltip content="Calculate the optimal route between two systems using A* pathfinding algorithm">
                <Button
                  onClick={handleCalculateRoute}
                  isLoading={isCalculating}
                  className="w-full"
                >
                  Calculate Route
                </Button>
              </Tooltip>
            </div>
          </div>

          {route && (
            <div className="mt-4 p-4 bg-eve-darker rounded-lg">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <div>
                  <span className="text-gray-400 text-sm">Total Jumps</span>
                  <div className="text-white font-bold text-xl">{route.total_jumps}</div>
                </div>
                <div>
                  <span className="text-gray-400 text-sm">Route Length</span>
                  <div className="text-white font-bold text-xl">{route.route_length}</div>
                </div>
                <div>
                  <span className="text-gray-400 text-sm">Avg Security</span>
                  <div className="text-white font-bold text-xl">
                    {route.average_security.toFixed(2)}
                  </div>
                </div>
                <div>
                  <span className="text-gray-400 text-sm">Est. Time</span>
                  <div className="text-white font-bold text-xl">
                    {formatDuration(route.estimated_time_seconds)}
                  </div>
                </div>
              </div>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {route.route.map((system: any, index: number) => (
                  <div
                    key={system.system_id}
                    className="flex items-center gap-3 p-2 bg-eve-dark rounded hover:bg-eve-gray transition-colors"
                  >
                    <span className="text-eve-blue font-mono text-sm w-8">{index + 1}</span>
                    <div className="flex-1">
                      <div className="text-white font-medium">{system.system_name}</div>
                      <div className="text-sm text-gray-400">
                        Security: <span className={formatSecurityStatus(system.security_status).colorClass}>
                          {formatSecurityStatus(system.security_status).value}
                        </span> • {system.region_name}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* System Search */}
      <Card title="System Search">
        {systemsLoading ? (
          <CardSkeleton lines={8} />
        ) : (
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {systems && systems.length > 0 ? (
              systems.slice(0, 100).map((system) => (
                <div
                  key={system.system_id}
                  className="flex items-center justify-between p-3 bg-eve-darker rounded-lg hover:bg-eve-dark transition-colors"
                >
                  <div>
                    <div className="text-white font-medium">{system.system_name}</div>
                    <div className="text-sm text-gray-400">
                      Security: <span className={formatSecurityStatus(system.security_status).colorClass}>
                        {formatSecurityStatus(system.security_status).value}
                      </span> • {system.region_name}
                    </div>
                  </div>
                  <div className="text-eve-blue font-mono text-sm">
                    {system.system_id}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-gray-400">No systems found</div>
            )}
          </div>
        )}
      </Card>
    </div>
  )
}
