import { create } from 'zustand'

/**
 * Pomodoro Session State
 *
 * Manages Pomodoro timer state and interactions with the backend API
 */

export interface PomodoroSession {
  sessionId: string
  userIntent: string
  startTime: string
  elapsedMinutes: number
  plannedDurationMinutes: number
}

export type PomodoroStatus = 'idle' | 'active' | 'ending' | 'processing'

interface PomodoroState {
  // State
  status: PomodoroStatus
  session: PomodoroSession | null
  error: string | null
  processingJobId: string | null

  // Actions
  setStatus: (status: PomodoroStatus) => void
  setSession: (session: PomodoroSession | null) => void
  setError: (error: string | null) => void
  setProcessingJobId: (jobId: string | null) => void
  reset: () => void
}

export const usePomodoroStore = create<PomodoroState>((set) => ({
  // Initial state
  status: 'idle',
  session: null,
  error: null,
  processingJobId: null,

  // Actions
  setStatus: (status) => set({ status }),

  setSession: (session) => set({ session }),

  setError: (error) => set({ error }),

  setProcessingJobId: (jobId) => set({ processingJobId: jobId }),

  reset: () =>
    set({
      status: 'idle',
      session: null,
      error: null,
      processingJobId: null
    })
}))
