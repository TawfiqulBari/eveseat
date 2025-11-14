import React from 'react'

interface CardProps {
  children: React.ReactNode
  className?: string
  title?: string
  actions?: React.ReactNode
}

export const Card: React.FC<CardProps> = ({ children, className = '', title, actions }) => {
  return (
    <div className={`bg-eve-dark border border-eve-gray rounded-lg shadow-lg ${className}`}>
      {(title || actions) && (
        <div className="px-6 py-4 border-b border-eve-gray flex items-center justify-between">
          {title && <h3 className="text-xl font-semibold text-white">{title}</h3>}
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}
      <div className="p-6">{children}</div>
    </div>
  )
}

