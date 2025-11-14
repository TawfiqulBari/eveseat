/**
 * Validation utilities for common input validation
 */

export interface ValidationResult {
  isValid: boolean
  error?: string
}

/**
 * Validate EVE Online system ID
 */
export function validateSystemId(value: string | number): ValidationResult {
  const numValue = typeof value === 'string' ? parseInt(value, 10) : value
  
  if (isNaN(numValue)) {
    return { isValid: false, error: 'System ID must be a number' }
  }
  
  if (numValue < 30000000 || numValue > 31000000) {
    return { isValid: false, error: 'System ID must be between 30000000 and 31000000' }
  }
  
  return { isValid: true }
}

/**
 * Validate EVE Online character ID
 */
export function validateCharacterId(value: string | number): ValidationResult {
  const numValue = typeof value === 'string' ? parseInt(value, 10) : value
  
  if (isNaN(numValue)) {
    return { isValid: false, error: 'Character ID must be a number' }
  }
  
  if (numValue <= 0) {
    return { isValid: false, error: 'Character ID must be greater than 0' }
  }
  
  return { isValid: true }
}

/**
 * Validate EVE Online corporation ID
 */
export function validateCorporationId(value: string | number): ValidationResult {
  const numValue = typeof value === 'string' ? parseInt(value, 10) : value
  
  if (isNaN(numValue)) {
    return { isValid: false, error: 'Corporation ID must be a number' }
  }
  
  if (numValue <= 0) {
    return { isValid: false, error: 'Corporation ID must be greater than 0' }
  }
  
  return { isValid: true }
}

/**
 * Validate ISK amount
 */
export function validateISK(value: string | number): ValidationResult {
  const numValue = typeof value === 'string' ? parseFloat(value) : value
  
  if (isNaN(numValue)) {
    return { isValid: false, error: 'ISK amount must be a number' }
  }
  
  if (numValue < 0) {
    return { isValid: false, error: 'ISK amount cannot be negative' }
  }
  
  return { isValid: true }
}

/**
 * Validate date range
 */
export function validateDateRange(startDate: string, endDate: string): ValidationResult {
  const start = new Date(startDate)
  const end = new Date(endDate)
  
  if (isNaN(start.getTime())) {
    return { isValid: false, error: 'Start date is invalid' }
  }
  
  if (isNaN(end.getTime())) {
    return { isValid: false, error: 'End date is invalid' }
  }
  
  if (start > end) {
    return { isValid: false, error: 'Start date must be before end date' }
  }
  
  const daysDiff = (end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)
  if (daysDiff > 365) {
    return { isValid: false, error: 'Date range cannot exceed 365 days' }
  }
  
  return { isValid: true }
}

/**
 * Validate required field
 */
export function validateRequired(value: any, fieldName: string = 'Field'): ValidationResult {
  if (value === null || value === undefined || value === '') {
    return { isValid: false, error: `${fieldName} is required` }
  }
  
  return { isValid: true }
}

/**
 * Validate email format (for future use)
 */
export function validateEmail(email: string): ValidationResult {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  
  if (!emailRegex.test(email)) {
    return { isValid: false, error: 'Invalid email format' }
  }
  
  return { isValid: true }
}

