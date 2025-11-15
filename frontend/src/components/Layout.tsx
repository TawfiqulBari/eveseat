import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useCharacter } from '../hooks/useCharacter'
import { authService } from '../services/auth'
import { charactersService } from '../services/characters'
import { Modal } from './common/Modal'
import { Button } from './common/Button'
import { MobileMenu } from './Layout/MobileMenu'

interface LayoutProps {
  children: React.ReactNode
}

const navigation = [
  { name: 'Dashboard', path: '/', icon: '📊' },
  { name: 'Killmails', path: '/killmails', icon: '💀' },
  { name: 'Map', path: '/map', icon: '🗺️' },
  { name: 'Corporations', path: '/corporations', icon: '🏢' },
  { name: 'Market', path: '/market', icon: '💰' },
  { name: 'Fleets', path: '/fleets', icon: '🚀' },
  { name: 'Wallet', path: '/wallet', icon: '💳' },
  { name: 'Contracts', path: '/contracts', icon: '📄' },
  { name: 'Contacts', path: '/contacts', icon: '👥' },
  { name: 'Calendar', path: '/calendar', icon: '📅' },
  { name: 'Industry', path: '/industry', icon: '🏭' },
  { name: 'Blueprints', path: '/blueprints', icon: '📐' },
  { name: 'Planetary', path: '/planetary', icon: '🌍' },
  { name: 'Loyalty', path: '/loyalty', icon: '⭐' },
  { name: 'Fittings', path: '/fittings', icon: '⚙️' },
  { name: 'Skills', path: '/skills', icon: '📚' },
  { name: 'Clones', path: '/clones', icon: '👤' },
  { name: 'Bookmarks', path: '/bookmarks', icon: '🔖' },
  { name: 'Structures', path: '/structures', icon: '🏗️' },
  { name: 'Moon Mining', path: '/moon-mining', icon: '🌑' },
  { name: 'Sovereignty', path: '/sovereignty', icon: '👑' },
]

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation()
  const { characterId, characterName } = useCharacter()
  const [showCharacterModal, setShowCharacterModal] = useState(false)

  const { data: characters } = useQuery({
    queryKey: ['characters'],
    queryFn: () => charactersService.list(),
    enabled: showCharacterModal,
  })

  const handleLogout = () => {
    authService.logout()
    window.location.href = '/'
  }

  const handleCharacterSwitch = (charId: number, charName: string) => {
    localStorage.setItem('character_id', charId.toString())
    localStorage.setItem('character_name', charName)
    setShowCharacterModal(false)
    window.location.reload()
  }

  return (
    <div className="min-h-screen bg-eve-darker">
      {/* Mobile Menu */}
      <MobileMenu />

      {/* Desktop Sidebar */}
      <div className="fixed inset-y-0 left-0 w-64 bg-eve-dark border-r border-eve-gray z-40 hidden md:block">
        <div className="flex flex-col h-full">
          {/* Logo/Header */}
          <div className="px-6 py-4 border-b border-eve-gray">
            <h1 className="text-xl font-bold text-white">EVE Manager</h1>
            <button
              onClick={() => setShowCharacterModal(true)}
              className="text-sm text-gray-400 mt-1 hover:text-white transition-colors text-left w-full"
            >
              {characterName || 'EVE Character'}
              {characters && characters.length > 1 && (
                <span className="ml-2 text-xs">({characters.length} characters)</span>
              )}
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-4 space-y-2">
            {navigation.map((item) => {
              const isActive = location.pathname === item.path
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center px-4 py-2 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-eve-blue text-white'
                      : 'text-gray-300 hover:bg-eve-gray hover:text-white'
                  }`}
                >
                  <span className="mr-3 text-lg">{item.icon}</span>
                  <span className="font-medium">{item.name}</span>
                </Link>
              )
            })}
          </nav>

          {/* Footer */}
          <div className="px-4 py-4 border-t border-eve-gray">
            <button
              onClick={handleLogout}
              className="w-full flex items-center px-4 py-2 rounded-lg text-gray-300 hover:bg-eve-gray hover:text-white transition-colors"
            >
              <span className="mr-3">🚪</span>
              <span className="font-medium">Logout</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="md:pl-64">
        <main className="p-4 md:p-8">{children}</main>
      </div>

      {/* Character Switch Modal */}
      <Modal
        isOpen={showCharacterModal}
        onClose={() => setShowCharacterModal(false)}
        title="Switch Character"
        size="md"
      >
        {characters && characters.length > 0 ? (
          <div className="space-y-2">
            {characters.map((char) => (
              <button
                key={char.id}
                onClick={() => handleCharacterSwitch(char.character_id, char.character_name)}
                className={`w-full text-left p-3 rounded-lg transition-colors ${
                  characterId === char.character_id
                    ? 'bg-eve-blue text-white'
                    : 'bg-eve-darker hover:bg-eve-dark text-gray-300'
                }`}
              >
                <div className="font-medium">{char.character_name}</div>
                {char.corporation_name && (
                  <div className="text-sm opacity-75">{char.corporation_name}</div>
                )}
              </button>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-400">
            No characters found
          </div>
        )}
      </Modal>
    </div>
  )
}

