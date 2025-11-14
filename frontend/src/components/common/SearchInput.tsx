import React, { useState, useRef, useEffect, useMemo } from 'react'
import { Input } from './Input'
import { useDebounce } from '../../hooks/useDebounce'

interface SearchInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onSelect'> {
  suggestions: Array<{ id: number | string; label: string; value?: any }>
  onSelect?: (item: { id: number | string; label: string; value?: any }) => void
  isLoading?: boolean
  minChars?: number
  debounceMs?: number
}

export const SearchInput: React.FC<SearchInputProps> = ({
  suggestions,
  onSelect,
  isLoading = false,
  minChars = 2,
  debounceMs = 300,
  value,
  onChange,
  ...props
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const [focusedIndex, setFocusedIndex] = useState(-1)
  const containerRef = useRef<HTMLDivElement>(null)
  const suggestionsListRef = useRef<HTMLDivElement>(null)
  
  // Debounce the search value to avoid filtering on every keystroke
  const debouncedValue = useDebounce(value as string, debounceMs)

  // Memoize filtered suggestions to avoid recalculating on every render
  const filteredSuggestions = useMemo(() => {
    const searchTerm = debouncedValue?.toLowerCase() || ''
    if (searchTerm.length >= minChars) {
      return suggestions.filter((item) =>
        item.label.toLowerCase().includes(searchTerm)
      ).slice(0, 10) // Limit to 10 suggestions
    }
    return []
  }, [debouncedValue, suggestions, minChars])

  useEffect(() => {
    if (filteredSuggestions.length > 0 && isOpen) {
      setIsOpen(true)
    } else if (filteredSuggestions.length === 0) {
      setIsOpen(false)
    }
  }, [filteredSuggestions.length, isOpen])

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
        setFocusedIndex(-1)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  const handleSelect = (item: { id: number | string; label: string; value?: any }) => {
    if (onSelect) {
      onSelect(item)
    }
    setIsOpen(false)
    setFocusedIndex(-1)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen || filteredSuggestions.length === 0) return

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setFocusedIndex((prev) => 
          prev < filteredSuggestions.length - 1 ? prev + 1 : prev
        )
        break
      case 'ArrowUp':
        e.preventDefault()
        setFocusedIndex((prev) => (prev > 0 ? prev - 1 : -1))
        break
      case 'Enter':
        e.preventDefault()
        if (focusedIndex >= 0 && focusedIndex < filteredSuggestions.length) {
          handleSelect(filteredSuggestions[focusedIndex])
        }
        break
      case 'Escape':
        setIsOpen(false)
        setFocusedIndex(-1)
        break
    }
  }

  // Scroll focused item into view
  useEffect(() => {
    if (focusedIndex >= 0 && suggestionsListRef.current) {
      const focusedElement = suggestionsListRef.current.children[focusedIndex] as HTMLElement
      if (focusedElement) {
        focusedElement.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
      }
    }
  }, [focusedIndex])

  return (
    <div className="relative w-full" ref={containerRef}>
      <Input
        value={value}
        onChange={onChange}
        onKeyDown={handleKeyDown}
        onFocus={() => {
          if (filteredSuggestions.length > 0) {
            setIsOpen(true)
          }
        }}
        aria-autocomplete="list"
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        role="combobox"
        {...props}
      />
      {isLoading && (
        <div className="absolute right-3 top-1/2 -translate-y-1/2" aria-hidden="true">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-eve-blue"></div>
        </div>
      )}
      {isOpen && filteredSuggestions.length > 0 && (
        <div
          ref={suggestionsListRef}
          className="absolute z-50 w-full mt-1 bg-eve-dark border border-eve-gray rounded-lg shadow-lg max-h-60 overflow-y-auto"
          role="listbox"
          aria-label="Suggestions"
        >
          {filteredSuggestions.map((item, index) => (
            <button
              key={item.id}
              onClick={() => handleSelect(item)}
              onMouseEnter={() => setFocusedIndex(index)}
              className={`w-full text-left px-4 py-2 text-white transition-colors ${
                index === focusedIndex
                  ? 'bg-eve-blue text-white'
                  : 'hover:bg-eve-gray'
              }`}
              role="option"
              aria-selected={index === focusedIndex}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

