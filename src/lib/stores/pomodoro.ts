import { create } from 'zustand'

/**
 * Pomodoro Session State with Rounds Support
 *
 * Manages Pomodoro timer state with work/break phases and rounds
 */

export interface PomodoroSession {
  sessionId: string
  userIntent: string
  startTime: string
  elapsedMinutes: number
  plannedDurationMinutes: number
  associatedTodoId?: string | null
  associatedTodoTitle?: string | null
  // Rounds configuration
  workDurationMinutes?: number
  breakDurationMinutes?: number
  totalRounds?: number
  currentRound?: number
  currentPhase?: string // 'work' | 'break' | 'completed'
  phaseStartTime?: string | null
  completedRounds?: number
  remainingPhaseSeconds?: number | null
}

export interface PomodoroConfig {
  workDurationMinutes: number
  breakDurationMinutes: number
  totalRounds: number
}

export interface PomodoroPreset {
  id: string
  name: string
  description: string
  workDurationMinutes: number
  breakDurationMinutes: number
  totalRounds: number
  icon: string
}

export type PomodoroStatus = 'idle' | 'active' | 'ending' | 'processing'
export type PomodoroPhase = 'work' | 'break' | 'completed'

interface PomodoroState {
  // Session state
  status: PomodoroStatus
  session: PomodoroSession | null
  error: string | null

  // Configuration state
  config: PomodoroConfig
  presets: PomodoroPreset[]
  selectedPresetId: string | null

  // Actions
  setStatus: (status: PomodoroStatus) => void
  setSession: (session: PomodoroSession | null) => void
  setError: (error: string | null) => void
  setConfig: (config: PomodoroConfig) => void
  setPresets: (presets: PomodoroPreset[]) => void
  setSelectedPresetId: (id: string | null) => void
  applyPreset: (presetId: string) => void
  reset: () => void
}

const DEFAULT_CONFIG: PomodoroConfig = {
  workDurationMinutes: 25,
  breakDurationMinutes: 5,
  totalRounds: 2
}

export const usePomodoroStore = create<PomodoroState>((set, get) => ({
  // Initial state
  status: 'idle',
  session: null,
  error: null,
  config: DEFAULT_CONFIG,
  presets: [],
  selectedPresetId: null,

  // Actions
  setStatus: (status) => set({ status }),

  setSession: (session) => set({ session }),

  setError: (error) => set({ error }),

  setConfig: (config) => set({ config, selectedPresetId: null }),

  setPresets: (presets) => set({ presets }),

  setSelectedPresetId: (selectedPresetId) => set({ selectedPresetId }),

  applyPreset: (presetId) => {
    const preset = get().presets.find((p) => p.id === presetId)
    if (preset) {
      set({
        config: {
          workDurationMinutes: preset.workDurationMinutes,
          breakDurationMinutes: preset.breakDurationMinutes,
          totalRounds: preset.totalRounds
        }
      })
    }
  },

  reset: () =>
    set({
      status: 'idle',
      session: null,
      error: null
    })
}))
