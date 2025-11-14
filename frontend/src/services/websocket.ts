import { logger } from '../utils/logger'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const WS_URL = import.meta.env.VITE_WS_URL || ''

// Convert http:// to ws:// or https:// to wss://
const getWebSocketUrl = (path: string): string => {
  // If VITE_WS_URL is set, use it directly
  if (WS_URL) {
    return `${WS_URL}${path}`
  }
  // Otherwise, convert API_URL
  const baseUrl = API_URL.replace(/^http/, 'ws')
  return `${baseUrl}${path}`
}

export interface WebSocketMessage {
  type: string
  data?: any
  message?: string
}

export class WebSocketClient {
  private ws: WebSocket | null = null
  private url: string
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private listeners: Map<string, Set<(data: any) => void>> = new Map()
  private onConnectCallbacks: Set<() => void> = new Set()
  private onDisconnectCallbacks: Set<() => void> = new Set()
  private onErrorCallbacks: Set<(error: Error) => void> = new Set()

  constructor(path: string) {
    this.url = getWebSocketUrl(path)
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return
    }

    try {
      this.ws = new WebSocket(this.url)

      this.ws.onopen = () => {
        this.reconnectAttempts = 0
        logger.info('WebSocket connection established', { url: this.url })
        this.onConnectCallbacks.forEach((callback) => callback())
      }

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          const callbacks = this.listeners.get(message.type)
          if (callbacks) {
            callbacks.forEach((callback) => callback(message.data || message))
          }
          // Also trigger 'message' event for all messages
          const allCallbacks = this.listeners.get('message')
          if (allCallbacks) {
            allCallbacks.forEach((callback) => callback(message))
          }
        } catch (error) {
          logger.error('Failed to parse WebSocket message', error, {
            rawData: event.data,
            url: this.url,
          })
        }
      }

      this.ws.onerror = () => {
        logger.error('WebSocket error occurred', new Error('WebSocket error'), {
          url: this.url,
          readyState: this.ws?.readyState,
        })
        this.onErrorCallbacks.forEach((callback) => callback(new Error('WebSocket error')))
      }

      this.ws.onclose = (event) => {
        logger.debug('WebSocket connection closed', {
          url: this.url,
          code: event.code,
          reason: event.reason,
          wasClean: event.wasClean,
        })
        this.onDisconnectCallbacks.forEach((callback) => callback())
        this.attemptReconnect()
      }
    } catch (error) {
      logger.error('Failed to create WebSocket connection', error, {
        url: this.url,
      })
      this.attemptReconnect()
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      const delay = this.reconnectDelay * this.reconnectAttempts
      logger.debug('Attempting WebSocket reconnect', {
        attempt: this.reconnectAttempts,
        maxAttempts: this.maxReconnectAttempts,
        delay,
        url: this.url,
      })
      setTimeout(() => {
        this.connect()
      }, delay)
    } else {
      logger.warn('WebSocket reconnection attempts exhausted', {
        maxAttempts: this.maxReconnectAttempts,
        url: this.url,
      })
    }
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.listeners.clear()
    this.onConnectCallbacks.clear()
    this.onDisconnectCallbacks.clear()
    this.onErrorCallbacks.clear()
  }

  send(data: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  on(event: string, callback: (data: any) => void): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event)!.add(callback)
  }

  off(event: string, callback?: (data: any) => void): void {
    if (!callback) {
      this.listeners.delete(event)
    } else {
      this.listeners.get(event)?.delete(callback)
    }
  }

  onConnect(callback: () => void): void {
    this.onConnectCallbacks.add(callback)
  }

  onDisconnect(callback: () => void): void {
    this.onDisconnectCallbacks.add(callback)
  }

  onError(callback: (error: Error) => void): void {
    this.onErrorCallbacks.add(callback)
  }

  get readyState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

// Killmail feed WebSocket client
let killmailFeedClient: WebSocketClient | null = null

export const connectKillmailFeed = (): WebSocketClient => {
  if (!killmailFeedClient) {
    killmailFeedClient = new WebSocketClient('/api/v1/killmails/feed')
    killmailFeedClient.connect()
  }
  return killmailFeedClient
}

export const disconnectKillmailFeed = (): void => {
  if (killmailFeedClient) {
    killmailFeedClient.disconnect()
    killmailFeedClient = null
  }
}

export const getKillmailFeedClient = (): WebSocketClient | null => {
  return killmailFeedClient
}

