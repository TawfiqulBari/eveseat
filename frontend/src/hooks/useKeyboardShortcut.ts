import { useEffect } from 'react'

interface KeyboardShortcutOptions {
  ctrlKey?: boolean
  shiftKey?: boolean
  altKey?: boolean
  metaKey?: boolean
  preventDefault?: boolean
}

export function useKeyboardShortcut(
  key: string,
  callback: (event: KeyboardEvent) => void,
  options: KeyboardShortcutOptions = {}
) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const {
        ctrlKey = false,
        shiftKey = false,
        altKey = false,
        metaKey = false,
        preventDefault = true,
      } = options

      // Support both Ctrl (Windows/Linux) and Cmd (Mac) for ctrlKey option
      const hasCtrlOrCmd = event.ctrlKey || event.metaKey
      const wantsCtrlOrCmd = ctrlKey || metaKey

      if (
        event.key === key &&
        (wantsCtrlOrCmd ? hasCtrlOrCmd : !hasCtrlOrCmd) &&
        event.shiftKey === shiftKey &&
        event.altKey === altKey
      ) {
        if (preventDefault) {
          event.preventDefault()
        }
        callback(event)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [key, callback, options])
}

