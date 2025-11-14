import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Table } from '../components/common/Table'
import { Button } from '../components/common/Button'
import { TableSkeleton } from '../components/common/Skeleton'
import { Pagination } from '../components/common/Pagination'
import { Tooltip } from '../components/common/Tooltip'
import { useToast } from '../components/common/Toast'
import { useCharacter } from '../hooks/useCharacter'
import { logger } from '../utils/logger'
import { validateCorporationId } from '../utils/validation'
import { formatISK } from '../utils/formatters'
import { corporationsService, Corporation, CorporationMember, CorporationAsset, CorporationStructure } from '../services/corporations'

export default function Corporations() {
  const [selectedCorpId, setSelectedCorpId] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<'info' | 'members' | 'assets' | 'structures'>('info')
  const { showToast } = useToast()
  const { characterId } = useCharacter()
  
  // For now, we'll need to get corporation ID from somewhere
  // In a real app, this would come from the character data
  const [corporationId, setCorporationId] = useState<number | null>(null)

  const { data: corporation, isLoading: corpLoading } = useQuery({
    queryKey: ['corporation', corporationId],
    queryFn: () => corporationsService.get(corporationId!),
    enabled: !!corporationId,
  })

  const [assetsSkip, setAssetsSkip] = useState(0)
  const [assetsLimit, setAssetsLimit] = useState(50)
  const [structuresSkip, setStructuresSkip] = useState(0)
  const [structuresLimit, setStructuresLimit] = useState(50)

  const { data: members, isLoading: membersLoading } = useQuery({
    queryKey: ['corporation-members', corporationId],
    queryFn: () => corporationsService.getMembers(corporationId!, 0, 100),
    enabled: !!corporationId && activeTab === 'members',
  })

  const { data: assets, isLoading: assetsLoading } = useQuery({
    queryKey: ['corporation-assets', corporationId, assetsSkip, assetsLimit],
    queryFn: () => corporationsService.getAssets(corporationId!, undefined, assetsSkip, assetsLimit),
    enabled: !!corporationId && activeTab === 'assets',
  })

  const { data: structures, isLoading: structuresLoading } = useQuery({
    queryKey: ['corporation-structures', corporationId, structuresSkip, structuresLimit],
    queryFn: () => corporationsService.getStructures(corporationId!, undefined, structuresSkip, structuresLimit),
    enabled: !!corporationId && activeTab === 'structures',
  })

  const handleSync = async () => {
    if (!corporationId || !characterId) {
      showToast('Please enter a corporation ID', 'warning')
      return
    }

    // Validate corporation ID
    const validation = validateCorporationId(corporationId)
    if (!validation.isValid) {
      showToast(validation.error || 'Invalid corporation ID', 'error')
      return
    }
    
    try {
      await corporationsService.sync(corporationId, characterId)
      showToast('Corporation sync initiated. Data will be updated shortly.', 'success')
      logger.info('Corporation sync initiated', { corporationId, characterId })
    } catch (error: any) {
      logger.error('Corporation sync failed', error, { corporationId, characterId })
      showToast(error.response?.data?.detail || 'Failed to sync corporation', 'error')
    }
  }

  const memberColumns = [
    {
      key: 'character_name',
      header: 'Character',
      sortable: true,
      sortKey: (member: CorporationMember) => member.character_name,
      render: (member: CorporationMember) => (
        <span className="text-white font-medium">{member.character_name}</span>
      ),
    },
    {
      key: 'roles',
      header: 'Roles',
      sortable: true,
      sortKey: (member: CorporationMember) => member.roles?.length || 0,
      render: (member: CorporationMember) => (
        <div className="flex flex-wrap gap-1">
          {member.roles && member.roles.length > 0 ? (
            member.roles.map((role, idx) => (
              <span
                key={idx}
                className="px-2 py-1 bg-eve-blue text-white text-xs rounded"
              >
                {role}
              </span>
            ))
          ) : (
            <span className="text-gray-500 text-sm">No roles</span>
          )}
        </div>
      ),
    },
    {
      key: 'start_date',
      header: 'Joined',
      sortable: true,
      sortKey: (member: CorporationMember) => member.start_date ? new Date(member.start_date) : new Date(0),
      render: (member: CorporationMember) => (
        <span className="text-gray-400">
          {member.start_date ? new Date(member.start_date).toLocaleDateString() : 'Unknown'}
        </span>
      ),
    },
  ]

  const assetColumns = [
    {
      key: 'type_name',
      header: 'Item',
      sortable: true,
      sortKey: (asset: CorporationAsset) => asset.type_name || `Type ${asset.type_id}`,
      render: (asset: CorporationAsset) => (
        <span className="text-white font-medium">{asset.type_name || `Type ${asset.type_id}`}</span>
      ),
    },
    {
      key: 'quantity',
      header: 'Quantity',
      sortable: true,
      sortKey: (asset: CorporationAsset) => asset.quantity,
      render: (asset: CorporationAsset) => (
        <span className="text-gray-300">{asset.quantity.toLocaleString()}</span>
      ),
    },
    {
      key: 'location',
      header: 'Location',
      sortable: true,
      sortKey: (asset: CorporationAsset) => asset.location_name || `Location ${asset.location_id}`,
      render: (asset: CorporationAsset) => (
        <div>
          <div className="text-white">{asset.location_name || `Location ${asset.location_id}`}</div>
          {asset.location_type && (
            <div className="text-sm text-gray-400">{asset.location_type}</div>
          )}
        </div>
      ),
    },
    {
      key: 'flag',
      header: 'Flag',
      sortable: true,
      sortKey: (asset: CorporationAsset) => asset.flag || '',
      render: (asset: CorporationAsset) => (
        <span className="text-gray-400">{asset.flag || 'N/A'}</span>
      ),
    },
    {
      key: 'is_singleton',
      header: 'Singleton',
      sortable: true,
      sortKey: (asset: CorporationAsset) => asset.is_singleton ? 1 : 0,
      render: (asset: CorporationAsset) => (
        <span className={asset.is_singleton ? 'text-green-400' : 'text-gray-500'}>
          {asset.is_singleton ? 'Yes' : 'No'}
        </span>
      ),
    },
  ]

  const structureColumns = [
    {
      key: 'structure_name',
      header: 'Structure',
      sortable: true,
      sortKey: (structure: CorporationStructure) => structure.structure_name || `Structure ${structure.structure_id}`,
      render: (structure: CorporationStructure) => (
        <span className="text-white font-medium">
          {structure.structure_name || `Structure ${structure.structure_id}`}
        </span>
      ),
    },
    {
      key: 'system',
      header: 'System',
      sortable: true,
      sortKey: (structure: CorporationStructure) => structure.system_name || '',
      render: (structure: CorporationStructure) => (
        <span className="text-eve-blue">{structure.system_name || `System ${structure.system_id}`}</span>
      ),
    },
    {
      key: 'state',
      header: 'State',
      sortable: true,
      sortKey: (structure: CorporationStructure) => structure.state || '',
      render: (structure: CorporationStructure) => (
        <span className={`px-2 py-1 rounded text-xs font-medium ${
          structure.state === 'online'
            ? 'bg-green-900/30 text-green-400'
            : structure.state?.includes('vulnerable')
            ? 'bg-red-900/30 text-red-400'
            : 'bg-yellow-900/30 text-yellow-400'
        }`}>
          {structure.state || 'Unknown'}
        </span>
      ),
    },
    {
      key: 'fuel_expires',
      header: 'Fuel Expires',
      sortable: true,
      sortKey: (structure: CorporationStructure) => structure.fuel_expires ? new Date(structure.fuel_expires) : new Date(0),
      render: (structure: CorporationStructure) => (
        <span className="text-gray-400">
          {structure.fuel_expires 
            ? new Date(structure.fuel_expires).toLocaleDateString() 
            : 'N/A'}
        </span>
      ),
    },
    {
      key: 'reinforce',
      header: 'Reinforce',
      render: (structure: CorporationStructure) => (
        <div className="text-sm text-gray-400">
          {structure.reinforce_hour !== null && structure.reinforce_weekday !== null ? (
            <>
              {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][structure.reinforce_weekday]} {structure.reinforce_hour}:00
            </>
          ) : (
            'N/A'
          )}
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Corporations</h1>
        <p className="text-gray-400">Manage corporation data and members</p>
      </div>

      {/* Corporation Search/Select */}
      <Card title="Select Corporation">
        <div className="flex gap-4">
          <input
            type="number"
            value={corporationId || ''}
            onChange={(e) => setCorporationId(e.target.value ? parseInt(e.target.value, 10) : null)}
            className="flex-1 px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
            placeholder="Enter Corporation ID"
          />
          <Tooltip content="Fetch the latest corporation data from EVE Online ESI API">
            <Button onClick={handleSync} disabled={!corporationId}>
              Sync Data
            </Button>
          </Tooltip>
        </div>
      </Card>

      {corporationId && (
        <>
          {/* Tabs */}
          <div className="flex gap-2 border-b border-eve-gray">
            {(['info', 'members', 'assets', 'structures'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 font-medium transition-colors ${
                  activeTab === tab
                    ? 'text-white border-b-2 border-eve-blue'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>

          {/* Corporation Info */}
          {activeTab === 'info' && (
            <Card title={corporation?.corporation_name || 'Corporation Information'}>
              {corpLoading ? (
                <div className="text-center py-8 text-gray-400">Loading...</div>
              ) : corporation ? (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-gray-400">Ticker:</span>
                    <span className="ml-2 text-white">{corporation.ticker || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">CEO:</span>
                    <span className="ml-2 text-white">{corporation.ceo_name || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">Member Count:</span>
                    <span className="ml-2 text-white">{corporation.member_count || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">Tax Rate:</span>
                    <span className="ml-2 text-white">
                      {corporation.tax_rate !== null ? `${(corporation.tax_rate * 100).toFixed(2)}%` : 'N/A'}
                    </span>
                  </div>
                  {corporation.alliance_name && (
                    <div>
                      <span className="text-gray-400">Alliance:</span>
                      <span className="ml-2 text-white">{corporation.alliance_name}</span>
                    </div>
                  )}
                  {corporation.description && (
                    <div className="col-span-2">
                      <span className="text-gray-400">Description:</span>
                      <p className="mt-1 text-white">{corporation.description}</p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-400">
                  Corporation not found. Click "Sync Data" to fetch from ESI.
                </div>
              )}
            </Card>
          )}

          {/* Members */}
          {activeTab === 'members' && (
            <Card title="Members">
              {membersLoading ? (
                <TableSkeleton rows={10} columns={3} />
              ) : members && members.items.length > 0 ? (
                <>
                  <Table
                    data={members.items}
                    columns={memberColumns}
                    keyExtractor={(item) => item.id.toString()}
                  />
                  <div className="mt-4 text-gray-400 text-sm">
                    Showing {members.items.length} of {members.total} members
                  </div>
                </>
              ) : (
                <div className="text-center py-8 text-gray-400">
                  No members found. Click "Sync Data" to fetch from ESI.
                </div>
              )}
            </Card>
          )}

          {/* Assets */}
          {activeTab === 'assets' && (
            <Card title="Assets">
              {assetsLoading ? (
                <TableSkeleton rows={10} columns={5} />
              ) : assets && assets.items.length > 0 ? (
                <>
                  <Table
                    data={assets.items}
                    columns={assetColumns}
                    keyExtractor={(item) => item.id.toString()}
                  />
                  {assets.total > 0 && (
                    <div className="mt-4">
                      <Pagination
                        currentPage={Math.floor(assetsSkip / assetsLimit) + 1}
                        totalPages={Math.ceil(assets.total / assetsLimit)}
                        totalItems={assets.total}
                        pageSize={assetsLimit}
                        onPageChange={(page) => setAssetsSkip((page - 1) * assetsLimit)}
                        onPageSizeChange={(size) => {
                          setAssetsLimit(size)
                          setAssetsSkip(0)
                        }}
                      />
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-8 text-gray-400">
                  No assets found. Click "Sync Data" to fetch from ESI.
                </div>
              )}
            </Card>
          )}

          {/* Structures */}
          {activeTab === 'structures' && (
            <Card title="Structures">
              {structuresLoading ? (
                <TableSkeleton rows={10} columns={5} />
              ) : structures && structures.items.length > 0 ? (
                <>
                  <Table
                    data={structures.items}
                    columns={structureColumns}
                    keyExtractor={(item) => item.id.toString()}
                  />
                  {structures.total > 0 && (
                    <div className="mt-4">
                      <Pagination
                        currentPage={Math.floor(structuresSkip / structuresLimit) + 1}
                        totalPages={Math.ceil(structures.total / structuresLimit)}
                        totalItems={structures.total}
                        pageSize={structuresLimit}
                        onPageChange={(page) => setStructuresSkip((page - 1) * structuresLimit)}
                        onPageSizeChange={(size) => {
                          setStructuresLimit(size)
                          setStructuresSkip(0)
                        }}
                      />
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-8 text-gray-400">
                  No structures found. Click "Sync Data" to fetch from ESI.
                </div>
              )}
            </Card>
          )}
        </>
      )}
    </div>
  )
}
