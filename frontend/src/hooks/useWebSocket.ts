import { useEffect, useState } from 'react'
import { connectKillmailFeed, disconnectKillmailFeed, getKillmailFeedClient, WebSocketClient } from '../services/websocket'

export interface UseKillmailFeedOptions {
  onKillmail?: (data: any) => void
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: Error) => void
}

export function useKillmailFeed(options: UseKillmailFeedOptions = {}) {
  const [isConnected, setIsConnected] = useState(false)
  const [client, setClient] = useState<WebSocketClient | null>(null)

  useEffect(() => {
    const wsClient = connectKillmailFeed()
    setClient(wsClient)

    const handleConnect = () => {
      setIsConnected(true)
      options.onConnect?.()
    }

    const handleDisconnect = () => {
      setIsConnected(false)
      options.onDisconnect?.()
    }

    const handleError = (error: Error) => {
      options.onError?.(error)
    }

    const handleKillmail = (message: any) => {
      if (message.type === 'killmail' && options.onKillmail) {
        options.onKillmail(message.data)
      }
    }

    wsClient.onConnect(handleConnect)
    wsClient.onDisconnect(handleDisconnect)
    wsClient.onError(handleError)
    wsClient.on('killmail', handleKillmail)
    wsClient.on('message', handleKillmail)

    // Check initial connection state
    if (wsClient.isConnected) {
      setIsConnected(true)
    }

    return () => {
      wsClient.off('killmail', handleKillmail)
      wsClient.off('message', handleKillmail)
      wsClient.onConnect(() => {})
      wsClient.onDisconnect(() => {})
      wsClient.onError(() => {})
    }
  }, [])

  return {
    isConnected,
    client,
  }
}

