import { useTauriEvent } from './useTauriEvents'

/**
 * Pomodoro work phase completed event payload
 * Emitted when a work phase ends and activities have been generated
 */
export interface PomodoroWorkPhaseCompletedPayload {
  session_id: string
  work_phase: number
  activity_count: number
}

/**
 * Pomodoro phase switched event payload
 * Emitted when session switches between work/break phases
 */
export interface PomodoroPhaseSwitchedPayload {
  session_id: string
  new_phase: string // 'work' | 'break' | 'completed'
  current_round: number
  total_rounds: number
  completed_rounds: number
}

/**
 * Pomodoro session deleted event payload
 * Emitted when a session is deleted
 */
export interface PomodoroSessionDeletedPayload {
  id: string
  deletedAt: string
}

/**
 * Hook for listening to Pomodoro work phase completion events
 * Fires when a work phase ends and activities have been generated
 */
export function usePomodoroWorkPhaseCompleted(onCompleted: (payload: PomodoroWorkPhaseCompletedPayload) => void) {
  useTauriEvent<PomodoroWorkPhaseCompletedPayload>('pomodoro-work-phase-completed', onCompleted)
}

/**
 * Hook for listening to Pomodoro phase switch events
 * Fires when session switches between work/break phases
 */
export function usePomodoroPhaseSwitched(onSwitched: (payload: PomodoroPhaseSwitchedPayload) => void) {
  useTauriEvent<PomodoroPhaseSwitchedPayload>('pomodoro-phase-switched', onSwitched)
}

/**
 * Hook for listening to Pomodoro session deletion events
 * Fires when a session is deleted
 */
export function usePomodoroSessionDeleted(onDeleted: (payload: PomodoroSessionDeletedPayload) => void) {
  useTauriEvent<PomodoroSessionDeletedPayload>('session-deleted', onDeleted)
}

/**
 * Combined hook for all Pomodoro events
 * Convenience wrapper for listening to multiple events at once
 */
export function usePomodoroEvents(handlers: {
  onWorkPhaseCompleted?: (payload: PomodoroWorkPhaseCompletedPayload) => void
  onPhaseSwitched?: (payload: PomodoroPhaseSwitchedPayload) => void
  onSessionDeleted?: (payload: PomodoroSessionDeletedPayload) => void
}) {
  if (handlers.onWorkPhaseCompleted) {
    usePomodoroWorkPhaseCompleted(handlers.onWorkPhaseCompleted)
  }

  if (handlers.onPhaseSwitched) {
    usePomodoroPhaseSwitched(handlers.onPhaseSwitched)
  }

  if (handlers.onSessionDeleted) {
    usePomodoroSessionDeleted(handlers.onSessionDeleted)
  }
}
