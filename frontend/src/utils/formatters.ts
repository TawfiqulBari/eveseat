/**
 * Utility functions for formatting EVE Online data
 */

/**
 * Format ISK value with appropriate suffix (K, M, B, T)
 */
export function formatISK(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'N/A'
  
  const absValue = Math.abs(value)
  
  if (absValue >= 1e12) {
    return `${(value / 1e12).toFixed(2)}T ISK`
  } else if (absValue >= 1e9) {
    return `${(value / 1e9).toFixed(2)}B ISK`
  } else if (absValue >= 1e6) {
    return `${(value / 1e6).toFixed(2)}M ISK`
  } else if (absValue >= 1e3) {
    return `${(value / 1e3).toFixed(2)}K ISK`
  } else {
    return `${value.toLocaleString()} ISK`
  }
}

/**
 * Format security status with color class
 */
export function formatSecurityStatus(security: number | null | undefined): {
  value: string
  colorClass: string
} {
  if (security === null || security === undefined) {
    return { value: 'N/A', colorClass: 'text-gray-400' }
  }
  
  const rounded = security.toFixed(2)
  
  if (security >= 0.5) {
    return { value: rounded, colorClass: 'text-green-400' }
  } else if (security >= 0.0) {
    return { value: rounded, colorClass: 'text-yellow-400' }
  } else {
    return { value: rounded, colorClass: 'text-red-400' }
  }
}

/**
 * Format system name with security status indicator
 */
export function formatSystemName(
  systemName: string | null | undefined,
  securityStatus: number | null | undefined
): string {
  if (!systemName) return 'Unknown System'
  
  if (securityStatus !== null && securityStatus !== undefined) {
    const indicator = securityStatus >= 0.5 ? '●' : securityStatus >= 0.0 ? '◆' : '■'
    return `${indicator} ${systemName}`
  }
  
  return systemName
}

/**
 * Format duration in seconds to human-readable string
 */
export function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}s`
  } else if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60)
    const secs = seconds % 60
    return secs > 0 ? `${minutes}m ${secs}s` : `${minutes}m`
  } else {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    if (minutes > 0) {
      return `${hours}h ${minutes}m`
    }
    return `${hours}h`
  }
}

/**
 * Format number with thousand separators
 */
export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'N/A'
  return value.toLocaleString('en-US')
}

/**
 * Get security status class name for styling
 */
export function getSecurityClass(security: number | null | undefined): string {
  if (security === null || security === undefined) return 'unknown'
  
  if (security >= 0.5) return 'high-sec'
  if (security >= 0.0) return 'low-sec'
  return 'null-sec'
}

