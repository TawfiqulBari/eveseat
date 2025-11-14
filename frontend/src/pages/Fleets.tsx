import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Table } from '../components/common/Table'
import { Button } from '../components/common/Button'
import { TableSkeleton, CardSkeleton } from '../components/common/Skeleton'
import { Tooltip } from '../components/common/Tooltip'
import { useToast } from '../components/common/Toast'
import { useCharacter } from '../hooks/useCharacter'
import { logger } from '../utils/logger'
import { fleetsService, Fleet, FleetMember, Doctrine, DoctrineCheckResponse } from '../services/fleets'

export default function Fleets() {
  const { characterId } = useCharacter()
  const { showToast } = useToast()
  const [selectedFleetId, setSelectedFleetId] = useState<number | null>(null)
  const [selectedDoctrineId, setSelectedDoctrineId] = useState<number | null>(null)
  const [doctrineCheck, setDoctrineCheck] = useState<DoctrineCheckResponse | null>(null)
  const [isChecking, setIsChecking] = useState(false)

  const { data: fleets, isLoading: fleetsLoading, refetch: refetchFleets } = useQuery({
    queryKey: ['fleets', characterId],
    queryFn: () => fleetsService.list(characterId!),
    enabled: !!characterId && characterId > 0,
  })

  const { data: fleet, isLoading: fleetLoading } = useQuery({
    queryKey: ['fleet', selectedFleetId, characterId],
    queryFn: () => fleetsService.get(selectedFleetId!, characterId!),
    enabled: !!selectedFleetId && !!characterId && characterId > 0,
  })

  const { data: members, isLoading: membersLoading } = useQuery({
    queryKey: ['fleet-members', selectedFleetId, characterId],
    queryFn: () => fleetsService.getMembers(selectedFleetId!, characterId!),
    enabled: !!selectedFleetId && !!characterId && characterId > 0,
  })

  const { data: doctrines } = useQuery({
    queryKey: ['doctrines'],
    queryFn: () => fleetsService.listDoctrines(true),
  })

  const handleCheckDoctrine = async () => {
    if (!selectedFleetId || !selectedDoctrineId || !characterId) {
      showToast('Please select a fleet and doctrine', 'warning')
      return
    }

    setIsChecking(true)
    try {
      const result = await fleetsService.checkDoctrine(selectedFleetId, characterId, selectedDoctrineId)
      setDoctrineCheck(result)
      showToast('Doctrine compliance check completed', 'success')
      logger.info('Doctrine compliance check completed', {
        fleetId: selectedFleetId,
        doctrineId: selectedDoctrineId,
        characterId,
      })
    } catch (error: any) {
      logger.error('Doctrine check failed', error, {
        fleetId: selectedFleetId,
        doctrineId: selectedDoctrineId,
        characterId,
      })
      showToast(error.response?.data?.detail || 'Failed to check doctrine compliance', 'error')
    } finally {
      setIsChecking(false)
    }
  }

  const memberColumns = [
    {
      key: 'character_name',
      header: 'Character',
      sortable: true,
      sortKey: (member: FleetMember) => member.character_name || `Character ${member.character_id}`,
      render: (member: FleetMember) => (
        <span className="text-white font-medium">{member.character_name || `Character ${member.character_id}`}</span>
      ),
    },
    {
      key: 'ship_type_name',
      header: 'Ship',
      sortable: true,
      sortKey: (member: FleetMember) => member.ship_type_name || `Type ${member.ship_type_id}`,
      render: (member: FleetMember) => (
        <span className="text-gray-300">{member.ship_type_name || `Type ${member.ship_type_id}`}</span>
      ),
    },
    {
      key: 'role_name',
      header: 'Role',
      sortable: true,
      sortKey: (member: FleetMember) => member.role_name,
      render: (member: FleetMember) => (
        <span className="px-2 py-1 bg-eve-blue text-white text-xs rounded">
          {member.role_name}
        </span>
      ),
    },
    {
      key: 'takes_fleet_warp',
      header: 'Fleet Warp',
      sortable: true,
      sortKey: (member: FleetMember) => member.takes_fleet_warp ? 1 : 0,
      render: (member: FleetMember) => (
        <span className={member.takes_fleet_warp ? 'text-green-400' : 'text-gray-500'}>
          {member.takes_fleet_warp ? 'Yes' : 'No'}
        </span>
      ),
    },
  ]

  if (!characterId || characterId === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Fleets</h1>
          <p className="text-gray-400">Manage fleet operations and doctrine compliance</p>
        </div>
        <Card>
          <div className="text-center py-8 text-gray-400">
            Please log in to view fleets
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Fleets</h1>
        <p className="text-gray-400">Manage fleet operations and doctrine compliance</p>
      </div>

      {/* Fleet List */}
      <Card title="Your Fleets">
        {fleetsLoading ? (
          <CardSkeleton lines={5} />
        ) : fleets && fleets.length > 0 ? (
          <div className="space-y-3">
            {fleets.map((fleet) => (
              <div
                key={fleet.id}
                className={`p-4 rounded-lg cursor-pointer transition-colors ${
                  selectedFleetId === fleet.fleet_id
                    ? 'bg-eve-blue border-2 border-eve-blue'
                    : 'bg-eve-darker border border-eve-gray hover:bg-eve-dark'
                }`}
                onClick={() => setSelectedFleetId(fleet.fleet_id)}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-white font-medium text-lg">
                      {fleet.fleet_name || `Fleet ${fleet.fleet_id}`}
                    </div>
                    <div className="text-sm text-gray-400 mt-1">
                      Fleet ID: {fleet.fleet_id}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {fleet.is_free_move && (
                      <span className="px-2 py-1 bg-green-900/30 text-green-400 text-xs rounded">
                        Free Move
                      </span>
                    )}
                    {fleet.is_voice_enabled && (
                      <span className="px-2 py-1 bg-blue-900/30 text-blue-400 text-xs rounded">
                        Voice
                      </span>
                    )}
                  </div>
                </div>
                {fleet.motd && (
                  <div className="mt-2 text-sm text-gray-300 italic">
                    {fleet.motd}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-400">
            No active fleets. Join a fleet in-game to see it here.
          </div>
        )}
      </Card>

      {selectedFleetId && (
        <>
          {/* Fleet Details */}
          <Card title={`Fleet ${selectedFleetId} Details`}>
            {fleetLoading ? (
              <CardSkeleton lines={4} />
            ) : fleet ? (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-gray-400">Fleet Name:</span>
                  <span className="ml-2 text-white">{fleet.fleet_name || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-gray-400">Free Move:</span>
                  <span className={`ml-2 ${fleet.is_free_move ? 'text-green-400' : 'text-gray-400'}`}>
                    {fleet.is_free_move ? 'Yes' : 'No'}
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">Registered:</span>
                  <span className={`ml-2 ${fleet.is_registered ? 'text-green-400' : 'text-gray-400'}`}>
                    {fleet.is_registered ? 'Yes' : 'No'}
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">Voice Enabled:</span>
                  <span className={`ml-2 ${fleet.is_voice_enabled ? 'text-green-400' : 'text-gray-400'}`}>
                    {fleet.is_voice_enabled ? 'Yes' : 'No'}
                  </span>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-400">Fleet not found</div>
            )}
          </Card>

          {/* Fleet Members */}
          <Card title="Fleet Members">
            {membersLoading ? (
              <TableSkeleton rows={10} columns={4} />
            ) : members && members.length > 0 ? (
              <Table
                data={members}
                columns={memberColumns}
                keyExtractor={(item) => item.id.toString()}
              />
            ) : (
              <div className="text-center py-8 text-gray-400">No members found</div>
            )}
          </Card>

          {/* Doctrine Compliance Check */}
          <Card title="Doctrine Compliance">
            <div className="space-y-4">
              <div className="flex gap-4">
                <select
                  value={selectedDoctrineId || ''}
                  onChange={(e) => setSelectedDoctrineId(e.target.value ? parseInt(e.target.value, 10) : null)}
                  className="flex-1 px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
                >
                  <option value="">Select a doctrine...</option>
                  {doctrines?.map((doctrine) => (
                    <option key={doctrine.id} value={doctrine.id}>
                      {doctrine.name}
                    </option>
                  ))}
                </select>
                <Tooltip content="Check if fleet members' ships match the selected doctrine requirements">
                  <Button
                    onClick={handleCheckDoctrine}
                    isLoading={isChecking}
                    disabled={!selectedDoctrineId}
                  >
                    Check Compliance
                  </Button>
                </Tooltip>
              </div>

              {doctrineCheck && (
                <div className="mt-4 p-4 bg-eve-darker rounded-lg">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div>
                      <span className="text-gray-400 text-sm">Total Members</span>
                      <div className="text-white font-bold text-xl">{doctrineCheck.compliance.total_members}</div>
                    </div>
                    <div>
                      <span className="text-gray-400 text-sm">Compliant</span>
                      <div className="text-green-400 font-bold text-xl">{doctrineCheck.compliance.compliant}</div>
                    </div>
                    <div>
                      <span className="text-gray-400 text-sm">Non-Compliant</span>
                      <div className="text-red-400 font-bold text-xl">{doctrineCheck.compliance.non_compliant}</div>
                    </div>
                    <div>
                      <span className="text-gray-400 text-sm">Compliance</span>
                      <div className="text-white font-bold text-xl">
                        {(doctrineCheck.compliance.compliance_rate * 100).toFixed(1)}%
                      </div>
                    </div>
                  </div>

                  {doctrineCheck.members_compliant.length > 0 && (
                    <div className="mt-4">
                      <h4 className="text-white font-medium mb-2">Compliant Members ({doctrineCheck.members_compliant.length}):</h4>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
                        {doctrineCheck.members_compliant.map((member, idx) => (
                          <div
                            key={idx}
                            className="p-2 bg-green-900/20 border border-green-600 rounded text-sm"
                          >
                            <div className="text-green-300 font-medium">{member.character_name}</div>
                            <div className="text-xs text-gray-400">{member.ship_type_name || `Type ${member.ship_type_id}`}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {doctrineCheck.members_non_compliant.length > 0 && (
                    <div className="mt-4">
                      <h4 className="text-white font-medium mb-2">Non-Compliant Members ({doctrineCheck.members_non_compliant.length}):</h4>
                      <div className="space-y-2">
                        {doctrineCheck.members_non_compliant.map((detail, idx) => (
                          <div
                            key={idx}
                            className="p-3 bg-red-900/20 border border-red-600 rounded-lg"
                          >
                            <div className="text-white font-medium">{detail.character_name}</div>
                            <div className="text-sm text-gray-400">
                              Flying: {detail.ship_type_name || `Type ${detail.ship_type_id}`}
                            </div>
                            {detail.expected_ship_types && detail.expected_ship_types.length > 0 && (
                              <div className="text-sm text-gray-400">
                                Expected: {detail.expected_ship_types.join(', ')}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </Card>
        </>
      )}
    </div>
  )
}


