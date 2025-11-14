import React, { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { Card } from '../components/common/Card'
import { Button } from '../components/common/Button'
import { Badge } from '../components/common/Badge'
import { CardSkeleton } from '../components/common/Skeleton'
import { Tooltip as UITooltip } from '../components/common/Tooltip'
import { useCharacter } from '../hooks/useCharacter'
import { authService } from '../services/auth'
import { charactersService } from '../services/characters'
import { killmailsService } from '../services/killmails'
import { formatISK, formatSecurityStatus } from '../utils/formatters'
import { downloadCSV, downloadJSON } from '../utils/export'
import { formatDistanceToNow } from 'date-fns'

export default function Dashboard() {
  const { characterId } = useCharacter()

  const { data: userInfo, isLoading: userLoading } = useQuery({
    queryKey: ['user', characterId],
    queryFn: () => authService.getCurrentUser(characterId!),
    enabled: !!characterId && characterId > 0,
  })

  const { data: characters, isLoading: charsLoading } = useQuery({
    queryKey: ['characters'],
    queryFn: () => charactersService.list(),
  })

  const { data: recentKillmails } = useQuery({
    queryKey: ['killmails', 'recent'],
    queryFn: () => killmailsService.list({ limit: 10 }),
  })

  const { data: killmailStats } = useQuery({
    queryKey: ['killmail-stats', characterId],
    queryFn: () => killmailsService.getStats({ character_id: characterId || undefined, days: 30 }),
    enabled: !!characterId && characterId > 0,
  })

  // Prepare chart data
  const topSystemsData = useMemo(() => {
    if (!killmailStats?.top_systems) return []
    return killmailStats.top_systems.slice(0, 5).map((item: any) => ({
      name: `System ${item.system_id}`,
      kills: item.count,
    }))
  }, [killmailStats])

  const topShipsData = useMemo(() => {
    if (!killmailStats?.top_ship_types) return []
    return killmailStats.top_ship_types.slice(0, 5).map((item: any) => ({
      name: `Type ${item.ship_type_id}`,
      kills: item.count,
    }))
  }, [killmailStats])

  const handleExportKillmails = () => {
    if (recentKillmails?.items) {
      downloadCSV(
        recentKillmails.items.map((km) => ({
          'Killmail ID': km.killmail_id,
          'Time': km.time,
          'Victim': km.victim_character_name || 'Unknown',
          'Corporation': km.victim_corporation_name || 'Unknown',
          'Ship': km.victim_ship_type_name || 'Unknown',
          'System': km.system_name || 'Unknown',
          'Value (ISK)': km.value || 0,
        })),
        'killmails-export',
        ['Killmail ID', 'Time', 'Victim', 'Corporation', 'Ship', 'System', 'Value (ISK)']
      )
    }
  }

  if (userLoading || charsLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Dashboard</h1>
          <p className="text-gray-400">Loading...</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card title="Character Info">
            <CardSkeleton lines={4} />
          </Card>
          <Card title="Linked Characters">
            <CardSkeleton lines={3} />
          </Card>
          <Card title="Recent Activity">
            <CardSkeleton lines={3} />
          </Card>
        </div>
      </div>
    )
  }

  const character = userInfo?.character

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Dashboard</h1>
        <p className="text-gray-400">Welcome back, {character?.character_name || 'Pilot'}</p>
      </div>

      {/* Character Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card title="Character Info">
          <div className="space-y-2">
            <div>
              <span className="text-gray-400">Name:</span>
              <span className="ml-2 text-white font-medium">{character?.character_name}</span>
            </div>
            {character?.corporation_name && (
              <div>
                <span className="text-gray-400">Corporation:</span>
                <span className="ml-2 text-white">{character.corporation_name}</span>
              </div>
            )}
            {character?.alliance_name && (
              <div>
                <span className="text-gray-400">Alliance:</span>
                <span className="ml-2 text-white">{character.alliance_name}</span>
              </div>
            )}
            {character?.security_status !== null && (
              <div>
                <span className="text-gray-400">Security Status:</span>
                <span className={`ml-2 font-medium ${formatSecurityStatus(parseFloat(character.security_status)).colorClass}`}>
                  {formatSecurityStatus(parseFloat(character.security_status)).value}
                </span>
              </div>
            )}
          </div>
        </Card>

        <Card title="Characters">
          <div className="text-3xl font-bold text-white">
            {characters?.length || 0}
          </div>
          <p className="text-gray-400 mt-2">Linked characters</p>
        </Card>

        <Card title="Recent Activity">
          <div className="text-3xl font-bold text-white">
            {recentKillmails?.total || 0}
          </div>
          <p className="text-gray-400 mt-2">Total killmails tracked</p>
          {killmailStats && (
            <div className="mt-4 pt-4 border-t border-eve-gray space-y-2">
              <div className="text-sm text-gray-400">Last 30 days</div>
              <div className="flex items-center gap-4">
                <div>
                  <div className="text-xl font-semibold text-white">
                    {killmailStats.total_kills}
                  </div>
                  <div className="text-xs text-gray-400">kills</div>
                </div>
                <div>
                  <div className="text-xl font-semibold text-yellow-400">
                    {formatISK(killmailStats.total_value)}
                  </div>
                  <div className="text-xs text-gray-400">total value</div>
                </div>
                {killmailStats.average_value > 0 && (
                  <div>
                    <div className="text-xl font-semibold text-green-400">
                      {formatISK(killmailStats.average_value)}
                    </div>
                    <div className="text-xs text-gray-400">avg value</div>
                  </div>
                )}
              </div>
            </div>
          )}
        </Card>
      </div>

      {/* Killmail Statistics Charts */}
      {killmailStats && killmailStats.total_kills > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card title="Top Systems by Kills">
            {topSystemsData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={topSystemsData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="name" stroke="#9CA3AF" angle={-45} textAnchor="end" height={80} />
                  <YAxis stroke="#9CA3AF" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1a1f2e',
                      border: '1px solid #374151',
                      borderRadius: '8px',
                    }}
                  />
                  <Bar dataKey="kills" fill="#1e3a5f" name="Kills" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center py-8 text-gray-400">No data available</div>
            )}
          </Card>

          <Card title="Top Ship Types">
            {topShipsData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={topShipsData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="name" stroke="#9CA3AF" angle={-45} textAnchor="end" height={80} />
                  <YAxis stroke="#9CA3AF" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1a1f2e',
                      border: '1px solid #374151',
                      borderRadius: '8px',
                    }}
                  />
                  <Bar dataKey="kills" fill="#4a9eff" name="Kills" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center py-8 text-gray-400">No data available</div>
            )}
          </Card>
        </div>
      )}

      {/* Recent Killmails */}
      <Card
        title="Recent Killmails"
        actions={
          recentKillmails && recentKillmails.items.length > 0 ? (
            <Button size="sm" variant="secondary" onClick={handleExportKillmails}>
              Export CSV
            </Button>
          ) : undefined
        }
      >
        {recentKillmails && recentKillmails.items.length > 0 ? (
          <div className="space-y-3">
            {recentKillmails.items.slice(0, 5).map((killmail) => (
              <div
                key={killmail.id}
                className="flex items-center justify-between p-3 bg-eve-darker rounded-lg hover:bg-eve-dark transition-colors"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <span className="text-white font-medium">
                      {killmail.victim_character_name || 'Unknown'}
                    </span>
                    <span className="text-gray-400">in</span>
                    <span className="text-eve-blue">{killmail.system_name || 'Unknown System'}</span>
                  </div>
                  <div className="text-sm text-gray-400 mt-1">
                    {killmail.victim_ship_type_name || 'Unknown Ship'} • {formatDistanceToNow(new Date(killmail.time), { addSuffix: true })}
                  </div>
                </div>
                {killmail.value && (
                  <div className="text-right">
                    <div className="text-yellow-400 font-medium">
                      {formatISK(killmail.value)}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-400">
            No recent killmails
          </div>
        )}
      </Card>
    </div>
  )
}
