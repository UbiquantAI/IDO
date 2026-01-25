import { useEffect, useRef } from 'react'
import { usePomodoroStore } from '@/lib/stores/pomodoro'
import { usePomodoroEvents } from '@/hooks/usePomodoroEvents'
import { getPomodoroStatus } from '@/lib/client/apiClient'

/**
 * Global Pomodoro state synchronization hook
 *
 * Keeps the Pomodoro store in sync with backend state by:
 * 1. Polling for status updates when active
 * 2. Listening to phase switch events for real-time updates
 * 3. Handling session completion and reset
 *
 * This ensures FloatingPomodoroTrigger and other components
 * always show the current Pomodoro state, even when the
 * PomodoroTimer component is not mounted.
 */
export function usePomodoroStateSync() {
  const { status, setStatus, setSession, reset } = usePomodoroStore()
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Initial status check on mount
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const result = await getPomodoroStatus()
        if (result.success && result.data) {
          setStatus('active')
          setSession(result.data)
        } else {
          // No active session
          reset()
        }
      } catch (err) {
        console.error('[PomodoroStateSync] Failed to check status:', err)
      }
    }

    checkStatus()
  }, [setStatus, setSession, reset])

  // Poll for status updates when active
  useEffect(() => {
    if (status !== 'active') {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
        pollIntervalRef.current = null
      }
      return
    }

    // Poll every 5 seconds for session updates
    pollIntervalRef.current = setInterval(async () => {
      try {
        const result = await getPomodoroStatus()
        if (result.success && result.data) {
          setSession(result.data)
        } else {
          // Session ended on backend
          reset()
        }
      } catch (err) {
        console.error('[PomodoroStateSync] Polling failed:', err)
      }
    }, 5000)

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
        pollIntervalRef.current = null
      }
    }
  }, [status, setSession, reset])

  // Listen to real-time phase switch events
  usePomodoroEvents({
    onPhaseSwitched: async (payload) => {
      console.log('[PomodoroStateSync] Phase switched:', payload)

      // For completed phase, reset without API call (prevents race condition with polling)
      // This handles both manual end and automatic session completion
      if (payload.new_phase === 'completed') {
        console.log('[PomodoroStateSync] Session completed, scheduling state reset')
        setTimeout(() => {
          reset()
        }, 3000)
        return
      }

      // For work/break phases, fetch full session info to update state
      try {
        const result = await getPomodoroStatus()
        if (result.success && result.data) {
          setSession(result.data)
        }
      } catch (err) {
        console.error('[PomodoroStateSync] Failed to update on phase switch:', err)
      }
    }
  })
}
