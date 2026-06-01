/**
 * Clock synchronization with Pomodoro state
 */

import { useEffect, useRef, useCallback } from 'react'
import { useSettingsStore } from '@/lib/stores/settings'
import { getPomodoroStatus } from '@/lib/client/apiClient'
import { usePomodoroEvents } from '@/hooks/usePomodoroEvents'
import {
  ensureClockWindow,
  closeClockWindow,
  updateClockState,
  showClockWindow,
  setClockPosition,
  setOnPositionChange
} from './windowManager'

/**
 * Synchronize clock window with Pomodoro state
 */
export function useClockSync() {
  const { settings, updateClockSettings } = useSettingsStore()
  const clockSettings = settings.clock
  const isInitialMount = useRef(true)

  // Handle position changes from window drag/resize
  const handlePositionChange = useCallback(
    (x: number, y: number, width: number, height: number) => {
      console.log('[ClockSync] Saving custom position:', { x, y, width, height })
      updateClockSettings({
        customX: x,
        customY: y,
        customWidth: width,
        customHeight: height,
        useCustomPosition: true
      })
    },
    [updateClockSettings]
  )

  // Set up position change listener
  useEffect(() => {
    setOnPositionChange(handlePositionChange)
    return () => {
      setOnPositionChange(null)
    }
  }, [handlePositionChange])

  // Handle clock enable/disable and position restoration
  useEffect(() => {
    // Wait for settings to be loaded (clockSettings will be undefined initially)
    if (!clockSettings) {
      console.log('[ClockSync] Waiting for clock settings to load...')
      return
    }

    if (!clockSettings.enabled) {
      console.log('[ClockSync] Clock disabled, closing window')
      closeClockWindow()
      return
    }

    console.log('[ClockSync] Clock enabled:', clockSettings)

    // Use custom position if available
    if (clockSettings.useCustomPosition && clockSettings.customX !== undefined && clockSettings.customY !== undefined) {
      console.log('[ClockSync] Restoring custom position:', {
        x: clockSettings.customX,
        y: clockSettings.customY,
        width: clockSettings.customWidth,
        height: clockSettings.customHeight
      })
      ensureClockWindow({
        x: clockSettings.customX,
        y: clockSettings.customY,
        width: clockSettings.customWidth,
        height: clockSettings.customHeight
      })
    } else {
      ensureClockWindow().then(() => {
        // Set position when window is created/ensured (only for new windows)
        console.log('[ClockSync] Setting default position:', clockSettings.position, clockSettings.size)
        setClockPosition(clockSettings.position, clockSettings.size)
      })
    }
  }, [
    clockSettings?.enabled,
    clockSettings?.useCustomPosition,
    clockSettings?.customX,
    clockSettings?.customY,
    clockSettings?.customWidth,
    clockSettings?.customHeight
  ])

  // Listen to Pomodoro phase changes
  usePomodoroEvents({
    onPhaseSwitched: async (payload) => {
      if (!clockSettings?.enabled) {
        return
      }

      console.log('[ClockSync] Phase switched:', payload)

      // Always show window when phase switches (work or break)
      // But do NOT reset position - just show the window
      if (payload.new_phase === 'work' || payload.new_phase === 'break') {
        await showClockWindow()
      }

      // Get the full session info from backend to get phase start time and durations
      try {
        const result = await getPomodoroStatus()
        if (result.success && result.data) {
          const session = result.data

          // Calculate total seconds for the current phase
          const totalSeconds =
            payload.new_phase === 'work'
              ? (session.workDurationMinutes || 25) * 60
              : (session.breakDurationMinutes || 5) * 60

          await updateClockState({
            sessionId: session.sessionId,
            phase: payload.new_phase as any,
            remainingSeconds: session.remainingPhaseSeconds ?? totalSeconds,
            totalSeconds,
            currentRound: session.currentRound || payload.current_round,
            totalRounds: session.totalRounds || payload.total_rounds,
            completedRounds: session.completedRounds || payload.completed_rounds,
            userIntent: session.userIntent || '',
            phaseStartTime: session.phaseStartTime || new Date().toISOString(),
            workDurationMinutes: session.workDurationMinutes || 25,
            breakDurationMinutes: session.breakDurationMinutes || 5
          })
        } else {
          // Fallback if we can't get session info
          const totalSeconds = calculateRemainingTime(payload)
          await updateClockState({
            sessionId: payload.session_id,
            phase: payload.new_phase as any,
            remainingSeconds: totalSeconds,
            totalSeconds,
            currentRound: payload.current_round,
            totalRounds: payload.total_rounds,
            completedRounds: payload.completed_rounds,
            userIntent: '',
            phaseStartTime: new Date().toISOString(),
            workDurationMinutes: 25,
            breakDurationMinutes: 5
          })
        }
      } catch (error) {
        console.error('[ClockSync] Failed to get session info after phase switch:', error)
        // Fallback to calculation
        const totalSeconds = calculateRemainingTime(payload)
        await updateClockState({
          sessionId: payload.session_id,
          phase: payload.new_phase as any,
          remainingSeconds: totalSeconds,
          totalSeconds,
          currentRound: payload.current_round,
          totalRounds: payload.total_rounds,
          completedRounds: payload.completed_rounds,
          userIntent: '',
          phaseStartTime: new Date().toISOString(),
          workDurationMinutes: 25,
          breakDurationMinutes: 5
        })
      }

      // Reset to normal clock mode when session completes
      if (payload.new_phase === 'completed') {
        setTimeout(async () => {
          // Clear session state to switch back to normal clock mode
          await updateClockState({
            sessionId: null,
            phase: null,
            remainingSeconds: 0,
            totalSeconds: 0,
            currentRound: 0,
            totalRounds: 0,
            completedRounds: 0,
            userIntent: '',
            phaseStartTime: null,
            workDurationMinutes: 25,
            breakDurationMinutes: 5
          })
        }, 3000) // Show completion for 3 seconds, then switch to normal clock
      }
    }
  })

  // Listen for position/size changes from settings UI (not from custom position)
  // Only apply when NOT using custom position
  useEffect(() => {
    // Skip on initial mount
    if (isInitialMount.current) {
      isInitialMount.current = false
      return
    }

    if (clockSettings?.enabled && !clockSettings?.useCustomPosition) {
      setClockPosition(clockSettings.position, clockSettings.size)
    }
  }, [clockSettings?.position, clockSettings?.size])
}

/**
 * Calculate remaining time in current phase
 * Uses actual session configuration instead of hardcoded values
 */
function calculateRemainingTime(
  payload: {
    new_phase: string
    current_round: number
    total_rounds: number
    completed_rounds: number
  },
  workDurationMinutes: number = 25,
  breakDurationMinutes: number = 5
): number {
  const workDuration = workDurationMinutes * 60 // Convert to seconds
  const breakDuration = breakDurationMinutes * 60 // Convert to seconds

  if (payload.new_phase === 'work') {
    return workDuration
  } else if (payload.new_phase === 'break') {
    return breakDuration
  }

  return 0
}

export default useClockSync
