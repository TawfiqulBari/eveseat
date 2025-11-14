/**
 * EVE Online constants and configuration
 */

// Major trade hub system IDs
export const TRADE_HUBS = {
  JITA: 30000142,
  AMARR: 30002187,
  DODIXIE: 30002659,
  RENS: 30002510,
  HEK: 30002053,
} as const

// Major region IDs
export const REGIONS = {
  THE_FORGE: 10000002,
  DOMAIN: 10000043,
  SINQ_LAISON: 10000032,
  HEIMATAR: 10000030,
  METROPOLIS: 10000042,
} as const

// Security status thresholds
export const SECURITY_THRESHOLDS = {
  HIGH_SEC: 0.5,
  LOW_SEC: 0.0,
  NULL_SEC: -1.0,
} as const

// ESI API endpoints (for reference)
export const ESI_ENDPOINTS = {
  BASE_URL: 'https://esi.evetech.net/latest',
  SSO_AUTH: 'https://login.eveonline.com/v2/oauth/authorize',
  SSO_TOKEN: 'https://login.eveonline.com/v2/oauth/token',
} as const

// Pagination defaults
export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 50,
  MAX_PAGE_SIZE: 100,
  MIN_PAGE_SIZE: 10,
} as const

// Cache durations (in milliseconds)
export const CACHE_DURATION = {
  SHORT: 5 * 60 * 1000, // 5 minutes
  MEDIUM: 15 * 60 * 1000, // 15 minutes
  LONG: 60 * 60 * 1000, // 1 hour
} as const

