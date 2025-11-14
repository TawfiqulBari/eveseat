import React from 'react'
import { Input } from './Input'

interface DateRangePickerProps {
  startDate: string
  endDate: string
  onStartDateChange: (date: string) => void
  onEndDateChange: (date: string) => void
  label?: string
  className?: string
}

export const DateRangePicker: React.FC<DateRangePickerProps> = ({
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
  label,
  className = '',
}) => {
  // Get default dates (last 30 days)
  const getDefaultStartDate = () => {
    const date = new Date()
    date.setDate(date.getDate() - 30)
    return date.toISOString().split('T')[0]
  }

  const getDefaultEndDate = () => {
    return new Date().toISOString().split('T')[0]
  }

  return (
    <div className={className}>
      {label && (
        <label className="block text-sm font-medium text-gray-300 mb-2">
          {label}
        </label>
      )}
      <div className="grid grid-cols-2 gap-4">
        <Input
          type="date"
          label="Start Date"
          value={startDate || getDefaultStartDate()}
          onChange={(e) => onStartDateChange(e.target.value)}
          max={endDate || getDefaultEndDate()}
        />
        <Input
          type="date"
          label="End Date"
          value={endDate || getDefaultEndDate()}
          onChange={(e) => onEndDateChange(e.target.value)}
          min={startDate || getDefaultStartDate()}
          max={getDefaultEndDate()}
        />
      </div>
    </div>
  )
}

