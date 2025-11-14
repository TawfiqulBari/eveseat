import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Table } from '../components/common/Table'
import { Button } from '../components/common/Button'
import { Badge } from '../components/common/Badge'
import { TableSkeleton } from '../components/common/Skeleton'
import { Modal } from '../components/common/Modal'
import { useToast } from '../components/common/Toast'
import { useCharacter } from '../hooks/useCharacter'
import { planetaryService, Planet, PlanetDetail } from '../services/planetary'
import { logger } from '../utils/logger'
import { formatDistanceToNow } from 'date-fns'

export default function Planetary() {
  const { characterId } = useCharacter()
  const queryClient = useQueryClient()
  const { showToast } = useToast()

  const [selectedPlanet, setSelectedPlanet] = useState<PlanetDetail | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  const { data: planets, isLoading: planetsLoading, error: planetsError } = useQuery({
    queryKey: ['planets', characterId],
    queryFn: () => planetaryService.listPlanets({
      character_id: characterId || undefined,
    }),
    enabled: !!characterId,
  })

  const { data: statistics, isLoading: statsLoading } = useQuery({
    queryKey: ['planetary-statistics', characterId],
    queryFn: () => planetaryService.getStatistics(characterId!),
    enabled: !!characterId,
  })

  const syncMutation = useMutation({
    mutationFn: () => planetaryService.triggerSync(characterId!),
    onSuccess: () => {
      showToast('Planetary sync started', 'success')
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['planets'] })
        queryClient.invalidateQueries({ queryKey: ['planetary-statistics'] })
      }, 2000)
    },
    onError: (error) => {
      logger.error('Failed to sync planetary', error)
      showToast('Failed to sync planetary', 'error')
    },
  })

  const handleViewPlanet = async (planetId: number) => {
    try {
      const detail = await planetaryService.getPlanet(planetId)
      setSelectedPlanet(detail)
      setIsModalOpen(true)
    } catch (error) {
      logger.error('Failed to load planet details', error)
      showToast('Failed to load planet details', 'error')
    }
  }

  const getPlanetTypeBadge = (type: string) => {
    const variants: Record<string, 'success' | 'info' | 'warning' | 'secondary'> = {
      temperate: 'success',
      barren: 'secondary',
      oceanic: 'info',
      ice: 'info',
      gas: 'warning',
      lava: 'warning',
      storm: 'warning',
      plasma: 'warning',
    }
    return <Badge variant={variants[type] || 'secondary'}>{type}</Badge>
  }

  const columns = [
    {
      key: 'planet_type',
      header: 'Type',
      sortable: true,
      sortKey: (planet: Planet) => planet.planet_type,
      render: (planet: Planet) => getPlanetTypeBadge(planet.planet_type),
    },
    {
      key: 'solar_system',
      header: 'System',
      sortable: true,
      sortKey: (planet: Planet) => planet.solar_system_id,
      render: (planet: Planet) => (
        <span className="text-white">System {planet.solar_system_id}</span>
      ),
    },
    {
      key: 'upgrade_level',
      header: 'Upgrade Level',
      sortable: true,
      sortKey: (planet: Planet) => planet.upgrade_level,
      render: (planet: Planet) => (
        <div className="flex items-center gap-2">
          <span className="text-gray-300">{planet.upgrade_level}</span>
          <div className="flex-1 bg-eve-gray rounded-full h-2 max-w-[100px]">
            <div
              className="bg-eve-blue h-2 rounded-full"
              style={{ width: `${(planet.upgrade_level / 6) * 100}%` }}
            />
          </div>
        </div>
      ),
    },
    {
      key: 'num_pins',
      header: 'Pins',
      sortable: true,
      sortKey: (planet: Planet) => planet.num_pins,
      render: (planet: Planet) => (
        <span className="text-gray-300">{planet.num_pins}</span>
      ),
    },
    {
      key: 'last_update',
      header: 'Last Update',
      sortable: true,
      sortKey: (planet: Planet) => planet.last_update ? new Date(planet.last_update) : new Date(0),
      render: (planet: Planet) => (
        planet.last_update ? (
          <span className="text-gray-300 text-sm">
            {formatDistanceToNow(new Date(planet.last_update), { addSuffix: true })}
          </span>
        ) : (
          <span className="text-gray-500">Never</span>
        )
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      sortable: false,
      render: (planet: Planet) => (
        <Button
          size="sm"
          variant="secondary"
          onClick={() => handleViewPlanet(planet.planet_id)}
        >
          View Details
        </Button>
      ),
    },
  ]

  if (!characterId) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Planetary Interaction</h1>
          <p className="text-gray-400">Please select a character</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Planetary Interaction</h1>
          <p className="text-gray-400">Manage your planetary colonies</p>
        </div>
        <Button
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
        >
          {syncMutation.isPending ? 'Syncing...' : 'Sync Planets'}
        </Button>
      </div>

      {/* Statistics */}
      {statsLoading ? (
        <Card title="Planetary Statistics">
          <div className="text-gray-400">Loading statistics...</div>
        </Card>
      ) : statistics ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Card title="Total Planets">
            <div className="text-3xl font-bold text-white">{statistics.total_planets}</div>
          </Card>
          <Card title="Active Extractors">
            <div className="text-3xl font-bold text-green-400">{statistics.active_extractors}</div>
          </Card>
          <Card title="Expiring Soon">
            <div className="text-3xl font-bold text-red-400">{statistics.expiring_soon}</div>
            <div className="text-sm text-gray-400 mt-1">{'< 24 hours'}</div>
          </Card>
          <Card title="Total Pins">
            <div className="text-3xl font-bold text-white">{statistics.total_pins}</div>
          </Card>
        </div>
      ) : null}

      {/* Planet Types */}
      {statistics && Object.keys(statistics.by_planet_type).length > 0 && (
        <Card title="By Planet Type">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(statistics.by_planet_type).map(([type, count]) => (
              <div key={type} className="p-4 bg-eve-darker rounded-lg text-center">
                {getPlanetTypeBadge(type)}
                <div className="text-2xl font-bold text-white mt-2">{count}</div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Planets Table */}
      <Card title={`Planets (${planets?.length || 0})`}>
        {planetsLoading ? (
          <TableSkeleton rows={10} columns={6} />
        ) : planetsError ? (
          <div className="text-center py-8 text-red-400">
            Error loading planets. Try syncing your planets.
          </div>
        ) : (
          <Table
            data={planets || []}
            columns={columns}
            keyExtractor={(item) => item.id.toString()}
            emptyMessage="No planets found. Click 'Sync Planets' to fetch from EVE Online."
            defaultSort={{ key: 'planet_type', direction: 'asc' }}
          />
        )}
      </Card>

      {/* Planet Detail Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          setSelectedPlanet(null)
        }}
        title="Planet Details"
        size="lg"
      >
        {selectedPlanet && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-gray-400">Type:</span>
                <div className="mt-1">{getPlanetTypeBadge(selectedPlanet.planet.planet_type)}</div>
              </div>
              <div>
                <span className="text-gray-400">System:</span>
                <div className="mt-1 text-white">System {selectedPlanet.planet.solar_system_id}</div>
              </div>
              <div>
                <span className="text-gray-400">Upgrade Level:</span>
                <div className="mt-1 text-white">{selectedPlanet.planet.upgrade_level}</div>
              </div>
              <div>
                <span className="text-gray-400">Pins:</span>
                <div className="mt-1 text-white">{selectedPlanet.planet.num_pins}</div>
              </div>
            </div>

            {selectedPlanet.pins && selectedPlanet.pins.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold text-white mb-3">Planet Pins</h3>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {selectedPlanet.pins.map((pin, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-3 bg-eve-darker rounded-lg"
                    >
                      <div>
                        <div className="text-white">Type ID: {pin.type_id}</div>
                        <div className="text-sm text-gray-400">
                          {pin.schematic_id && `Schematic: ${pin.schematic_id}`}
                          {pin.product_type_id && ` • Product: ${pin.product_type_id}`}
                        </div>
                      </div>
                      {pin.expiry_time && (
                        <div className="text-sm text-gray-400">
                          Expires {formatDistanceToNow(new Date(pin.expiry_time), { addSuffix: true })}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {selectedPlanet.extractions && selectedPlanet.extractions.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold text-white mb-3">Active Extractions</h3>
                <div className="space-y-2">
                  {selectedPlanet.extractions.map((ext, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-3 bg-eve-darker rounded-lg"
                    >
                      <div>
                        <div className="text-white">Product: {ext.product_type_id}</div>
                        <Badge variant={ext.status === 'active' ? 'success' : 'secondary'}>
                          {ext.status}
                        </Badge>
                      </div>
                      <div className="text-sm text-gray-400">
                        Expires {formatDistanceToNow(new Date(ext.expiry_time), { addSuffix: true })}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
