import React from 'react'

interface EmptyStateProps {
  title?: string
  message: string
  icon?: string
  action?: {
    label: string
    onClick: () => void
  }
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  message,
  icon = '📭',
  action,
}) => {
  return (
    <div className="text-center py-12">
      <div className="text-6xl mb-4">{icon}</div>
      {title && <h3 className="text-xl font-semibold text-white mb-2">{title}</h3>}
      <p className="text-gray-400 mb-6">{message}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="px-4 py-2 bg-eve-blue hover:bg-eve-blue-dark text-white rounded-lg transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  )
}

