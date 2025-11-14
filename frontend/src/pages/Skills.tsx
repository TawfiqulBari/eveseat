import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '../components/common/Card'
import { Table } from '../components/common/Table'
import { Button } from '../components/common/Button'
import { Badge } from '../components/common/Badge'
import { TableSkeleton } from '../components/common/Skeleton'
import { useToast } from '../components/common/Toast'
import { useCharacter } from '../hooks/useCharacter'
import { skillsService, Skill, SkillQueue } from '../services/skills'
import { logger } from '../utils/logger'
import { formatDistanceToNow, format } from 'date-fns'

export default function Skills() {
  const { characterId } = useCharacter()
  const queryClient = useQueryClient()
  const { showToast } = useToast()

  const [activeTab, setActiveTab] = useState<'skills' | 'queue'>('skills')
  const [filters, setFilters] = useState({
    skip: 0,
    limit: 100,
    min_level: undefined as number | undefined,
  })

  const { data: skills, isLoading: skillsLoading, error: skillsError } = useQuery({
    queryKey: ['skills', characterId, filters],
    queryFn: () => skillsService.listSkills({
      character_id: characterId || undefined,
      ...filters,
      offset: filters.skip,
    }),
    enabled: !!characterId && activeTab === 'skills',
  })

  const { data: queue, isLoading: queueLoading, error: queueError } = useQuery({
    queryKey: ['skill-queue', characterId],
    queryFn: () => skillsService.getSkillQueue(characterId!),
    enabled: !!characterId && activeTab === 'queue',
  })

  const { data: statistics, isLoading: statsLoading } = useQuery({
    queryKey: ['skill-statistics', characterId],
    queryFn: () => skillsService.getStatistics(characterId!),
    enabled: !!characterId,
  })

  const syncMutation = useMutation({
    mutationFn: () => skillsService.triggerSync(characterId!),
    onSuccess: () => {
      showToast('Skills sync started', 'success')
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['skills'] })
        queryClient.invalidateQueries({ queryKey: ['skill-queue'] })
        queryClient.invalidateQueries({ queryKey: ['skill-statistics'] })
      }, 2000)
    },
    onError: (error) => {
      logger.error('Failed to sync skills', error)
      showToast('Failed to sync skills', 'error')
    },
  })

  const skillColumns = [
    {
      key: 'skill_id',
      header: 'Skill',
      sortable: true,
      sortKey: (skill: Skill) => skill.skill_id,
      render: (skill: Skill) => (
        <span className="text-white">Skill {skill.skill_id}</span>
      ),
    },
    {
      key: 'active_level',
      header: 'Active Level',
      sortable: true,
      sortKey: (skill: Skill) => skill.active_skill_level,
      render: (skill: Skill) => (
        <Badge variant={skill.active_skill_level >= 5 ? 'success' : 'info'}>
          Level {skill.active_skill_level}
        </Badge>
      ),
    },
    {
      key: 'trained_level',
      header: 'Trained Level',
      sortable: true,
      sortKey: (skill: Skill) => skill.trained_skill_level,
      render: (skill: Skill) => (
        <Badge variant="secondary">Level {skill.trained_skill_level}</Badge>
      ),
    },
    {
      key: 'skillpoints',
      header: 'Skillpoints',
      sortable: true,
      sortKey: (skill: Skill) => skill.skillpoints_in_skill,
      render: (skill: Skill) => (
        <span className="text-yellow-400">{skill.skillpoints_in_skill.toLocaleString()} SP</span>
      ),
    },
  ]

  const queueColumns = [
    {
      key: 'position',
      header: 'Position',
      sortable: true,
      sortKey: (item: SkillQueue) => item.queue_position,
      render: (item: SkillQueue) => (
        <Badge variant="info">#{item.queue_position}</Badge>
      ),
    },
    {
      key: 'skill_id',
      header: 'Skill',
      sortable: true,
      sortKey: (item: SkillQueue) => item.skill_id,
      render: (item: SkillQueue) => (
        <span className="text-white">Skill {item.skill_id}</span>
      ),
    },
    {
      key: 'level',
      header: 'Target Level',
      sortable: true,
      sortKey: (item: SkillQueue) => item.finished_level,
      render: (item: SkillQueue) => (
        <Badge variant="success">Level {item.finished_level}</Badge>
      ),
    },
    {
      key: 'start_date',
      header: 'Started',
      sortable: true,
      sortKey: (item: SkillQueue) => item.start_date ? new Date(item.start_date) : new Date(0),
      render: (item: SkillQueue) => (
        item.start_date ? (
          <div>
            <div className="text-white text-sm">
              {format(new Date(item.start_date), 'MMM dd, HH:mm')}
            </div>
            <div className="text-xs text-gray-400">
              {formatDistanceToNow(new Date(item.start_date), { addSuffix: true })}
            </div>
          </div>
        ) : (
          <span className="text-gray-500">Queued</span>
        )
      ),
    },
    {
      key: 'finish_date',
      header: 'Finishes',
      sortable: true,
      sortKey: (item: SkillQueue) => item.finish_date ? new Date(item.finish_date) : new Date(0),
      render: (item: SkillQueue) => (
        item.finish_date ? (
          <div>
            <div className="text-white text-sm">
              {format(new Date(item.finish_date), 'MMM dd, HH:mm')}
            </div>
            <div className="text-xs text-gray-400">
              {formatDistanceToNow(new Date(item.finish_date), { addSuffix: true })}
            </div>
          </div>
        ) : (
          <span className="text-gray-500">-</span>
        )
      ),
    },
  ]

  if (!characterId) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Skills</h1>
          <p className="text-gray-400">Please select a character</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Skills</h1>
          <p className="text-gray-400">Track your character's skills and training queue</p>
        </div>
        <Button
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
        >
          {syncMutation.isPending ? 'Syncing...' : 'Sync Skills'}
        </Button>
      </div>

      {/* Statistics */}
      {statsLoading ? (
        <Card title="Skill Statistics">
          <div className="text-gray-400">Loading statistics...</div>
        </Card>
      ) : statistics ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Card title="Total Skills">
            <div className="text-3xl font-bold text-white">{statistics.total_skills}</div>
          </Card>
          <Card title="Total Skillpoints">
            <div className="text-3xl font-bold text-yellow-400">
              {(statistics.total_sp / 1000000).toFixed(1)}M SP
            </div>
          </Card>
          <Card title="Level V Skills">
            <div className="text-3xl font-bold text-green-400">{statistics.skills_at_level_5}</div>
          </Card>
          <Card title="Queue Time Left">
            <div className="text-3xl font-bold text-blue-400">
              {statistics.queue_time_remaining
                ? `${Math.floor(statistics.queue_time_remaining / 24)}d ${Math.floor(statistics.queue_time_remaining % 24)}h`
                : '0h'}
            </div>
          </Card>
        </div>
      ) : null}

      {/* Tabs */}
      <Card>
        <div className="flex gap-4 border-b border-eve-gray pb-4">
          <button
            onClick={() => setActiveTab('skills')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'skills'
                ? 'bg-eve-blue text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Skills
          </button>
          <button
            onClick={() => setActiveTab('queue')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'queue'
                ? 'bg-eve-blue text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Training Queue
          </button>
        </div>

        {/* Skills Tab */}
        {activeTab === 'skills' && (
          <div className="mt-6 space-y-4">
            {/* Filters */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Minimum Level
                </label>
                <select
                  value={filters.min_level || ''}
                  onChange={(e) =>
                    setFilters({
                      ...filters,
                      min_level: e.target.value ? parseInt(e.target.value) : undefined,
                    })
                  }
                  className="w-full px-3 py-2 bg-eve-darker border border-eve-gray rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-eve-blue"
                >
                  <option value="">All Levels</option>
                  <option value="1">Level I+</option>
                  <option value="2">Level II+</option>
                  <option value="3">Level III+</option>
                  <option value="4">Level IV+</option>
                  <option value="5">Level V</option>
                </select>
              </div>
            </div>

            {/* Skills Table */}
            {skillsLoading ? (
              <TableSkeleton rows={10} columns={4} />
            ) : skillsError ? (
              <div className="text-center py-8 text-red-400">
                Error loading skills. Try syncing your skills.
              </div>
            ) : (
              <Table
                data={skills || []}
                columns={skillColumns}
                keyExtractor={(item) => item.id.toString()}
                emptyMessage="No skills found. Click 'Sync Skills' to fetch from EVE Online."
                defaultSort={{ key: 'skillpoints', direction: 'desc' }}
              />
            )}
          </div>
        )}

        {/* Queue Tab */}
        {activeTab === 'queue' && (
          <div className="mt-6">
            {queueLoading ? (
              <TableSkeleton rows={10} columns={5} />
            ) : queueError ? (
              <div className="text-center py-8 text-red-400">
                Error loading skill queue. Try syncing your skills.
              </div>
            ) : (
              <Table
                data={queue || []}
                columns={queueColumns}
                keyExtractor={(item) => item.id.toString()}
                emptyMessage="No skills in training queue. Click 'Sync Skills' to fetch from EVE Online."
                defaultSort={{ key: 'position', direction: 'asc' }}
              />
            )}
          </div>
        )}
      </Card>
    </div>
  )
}
