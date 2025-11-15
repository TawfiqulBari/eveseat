import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useCharacter } from '../../hooks/useCharacter'
import { authService } from '../../services/auth'

const navigationCategories = [
  {
    name: 'Overview',
    items: [
      { name: 'Dashboard', path: '/', icon: '📊' },
      { name: 'Map', path: '/map', icon: '🗺️' },
      { name: 'Killmails', path: '/killmails', icon: '💀' },
    ],
  },
  {
    name: 'Character',
    items: [
      { name: 'Wallet', path: '/wallet', icon: '💳' },
      { name: 'Skills', path: '/skills', icon: '📚' },
      { name: 'Clones', path: '/clones', icon: '👤' },
      { name: 'Fittings', path: '/fittings', icon: '⚙️' },
    ],
  },
  {
    name: 'Corporation',
    items: [
      { name: 'Corporations', path: '/corporations', icon: '🏢' },
      { name: 'Structures', path: '/structures', icon: '🏗️' },
      { name: 'Moon Mining', path: '/moon-mining', icon: '🌑' },
    ],
  },
  {
    name: 'Economy',
    items: [
      { name: 'Market', path: '/market', icon: '💰' },
      { name: 'Industry', path: '/industry', icon: '🏭' },
      { name: 'Contracts', path: '/contracts', icon: '📄' },
    ],
  },
  {
    name: 'PvP',
    items: [
      { name: 'Fleets', path: '/fleets', icon: '🚀' },
      { name: 'Wars', path: '/wars', icon: '⚔️' },
    ],
  },
]

export const MobileMenu: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(new Set())
  const location = useLocation()
  const { characterName } = useCharacter()

  const toggleCategory = (categoryName: string) => {
    setCollapsedCategories((prev) => {
      const next = new Set(prev)
      if (next.has(categoryName)) {
        next.delete(categoryName)
      } else {
        next.add(categoryName)
      }
      return next
    })
  }

  const handleLogout = () => {
    authService.logout()
    window.location.href = '/'
  }

  return (
    <>
      {/* Mobile Menu Button */}
      <div className="md:hidden fixed top-4 left-4 z-50">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="p-2 bg-eve-dark border border-eve-gray rounded-lg text-white hover:bg-eve-gray transition-colors"
          aria-label="Toggle menu"
        >
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            {isOpen ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>
      </div>

      {/* Mobile Menu Overlay */}
      {isOpen && (
        <div
          className="md:hidden fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
          onClick={() => setIsOpen(false)}
        >
          <div
            className="fixed inset-y-0 left-0 w-64 bg-eve-dark border-r border-eve-gray"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex flex-col h-full">
              {/* Header */}
              <div className="px-6 py-4 border-b border-eve-gray">
                <h1 className="text-xl font-bold text-white">EVE Manager</h1>
                <p className="text-sm text-gray-400 mt-1">{characterName || 'EVE Character'}</p>
              </div>

              {/* Navigation */}
              <nav className="flex-1 px-4 py-4 space-y-1 overflow-y-auto">
                {navigationCategories.map((category) => {
                  const isCollapsed = collapsedCategories.has(category.name)
                  return (
                    <div key={category.name} className="mb-2">
                      <button
                        onClick={() => toggleCategory(category.name)}
                        className="w-full flex items-center justify-between px-3 py-2 text-sm font-semibold text-gray-400 hover:text-white transition-colors"
                      >
                        <span>{category.name}</span>
                        <span className="text-xs">{isCollapsed ? '▶' : '▼'}</span>
                      </button>
                      {!isCollapsed && (
                        <div className="mt-1 space-y-1">
                          {category.items.map((item) => {
                            const isActive = location.pathname === item.path
                            return (
                              <Link
                                key={item.path}
                                to={item.path}
                                onClick={() => setIsOpen(false)}
                                className={`flex items-center px-4 py-2 rounded-lg transition-colors text-sm ${
                                  isActive
                                    ? 'bg-eve-blue text-white'
                                    : 'text-gray-300 hover:bg-eve-gray hover:text-white'
                                }`}
                              >
                                <span className="mr-3">{item.icon}</span>
                                <span className="font-medium">{item.name}</span>
                              </Link>
                            )
                          })}
                        </div>
                      )}
                    </div>
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
        </div>
      )}
    </>
  )
}

