import { create } from 'zustand'

/**
 * Pomodoro Floating Panel State
 *
 * Manages UI state for the global floating Pomodoro panel.
 * This store maintains userIntent and selectedTodoId independently from the page,
 * allowing state to persist when the panel is closed and reopened.
 */

interface PomodoroPanelState {
  // UI state for the panel
  userIntent: string
  selectedTodoId: string | null

  // Actions
  setUserIntent: (intent: string) => void
  setSelectedTodoId: (id: string | null) => void
  clearTask: () => void
  syncFromPage: (intent: string, todoId: string | null) => void
}

export const usePomodoroPanelStore = create<PomodoroPanelState>((set) => ({
  // Initial state
  userIntent: '',
  selectedTodoId: null,

  // Actions
  setUserIntent: (intent) => set({ userIntent: intent }),

  setSelectedTodoId: (id) => set({ selectedTodoId: id }),

  clearTask: () =>
    set({
      userIntent: '',
      selectedTodoId: null
    }),

  syncFromPage: (intent, todoId) =>
    set({
      userIntent: intent,
      selectedTodoId: todoId
    })
}))
