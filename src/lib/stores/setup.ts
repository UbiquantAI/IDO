import { create } from 'zustand'
import * as apiClient from '@/lib/client/apiClient'

export type SetupStep = 'welcome' | 'screens' | 'model' | 'permissions' | 'goals' | 'complete'

interface SetupState {
  /**
   * Whether the initialization overlay is currently showing.
   * When false, the overlay stays hidden even if the step isn't complete.
   */
  isActive: boolean
  /**
   * Tracks whether the user has acknowledged the completion screen.
   * Once true we don't show the flow again unless manually reset.
   */
  hasAcknowledged: boolean
  currentStep: SetupStep

  start: () => void
  goToStep: (step: SetupStep) => void
  markScreensStepDone: () => void
  markModelStepDone: () => void
  markPermissionsStepDone: () => void
  markGoalsStepDone: () => void
  completeAndAcknowledge: () => Promise<void>
  skipForNow: () => Promise<void>
  reopen: () => void
  reset: () => void
  checkAndActivateSetup: () => Promise<void>
}

const nextStepMap: Record<SetupStep, SetupStep> = {
  welcome: 'screens',
  screens: 'model',
  model: 'permissions',
  permissions: 'goals',
  goals: 'complete',
  complete: 'complete'
}

export const useSetupStore = create<SetupState>()((set, get) => ({
  // Start with setup inactive - checkAndActivateSetup will activate if needed
  isActive: false,
  hasAcknowledged: false,
  currentStep: 'welcome',

  start: () => {
    set({
      isActive: true,
      currentStep: nextStepMap.welcome
    })
  },

  goToStep: (step) => {
    set({
      isActive: true,
      currentStep: step
    })
  },

  markScreensStepDone: () => {
    const { currentStep } = get()
    if (currentStep === 'screens') {
      set({
        currentStep: nextStepMap.screens
      })
    }
  },

  markModelStepDone: () => {
    const { currentStep } = get()
    if (currentStep === 'model') {
      set({
        currentStep: nextStepMap.model
      })
    }
  },

  markPermissionsStepDone: () => {
    const { currentStep } = get()
    if (currentStep === 'permissions') {
      set({
        currentStep: nextStepMap.permissions
      })
    }
  },

  markGoalsStepDone: () => {
    const { currentStep } = get()
    if (currentStep === 'goals') {
      set({
        currentStep: nextStepMap.goals
      })
    }
  },

  completeAndAcknowledge: async () => {
    try {
      // Persist completion status to backend
      await apiClient.completeInitialSetup()
      console.log('[SetupStore] Initial setup completion persisted to backend')
    } catch (error) {
      console.error('[SetupStore] Failed to persist setup completion:', error)
      // Continue anyway - user can still use the app
    }

    set({
      isActive: false,
      hasAcknowledged: true,
      currentStep: 'complete'
    })
  },

  skipForNow: async () => {
    try {
      // Persist completion status to backend (even when skipping)
      await apiClient.completeInitialSetup()
      console.log('[SetupStore] Initial setup skip persisted to backend')
    } catch (error) {
      console.error('[SetupStore] Failed to persist setup skip:', error)
      // Continue anyway - user can still use the app
    }

    // Allow users to exit the flow entirely without finishing.
    set({
      isActive: false,
      hasAcknowledged: true,
      currentStep: 'complete'
    })
  },

  reopen: () => {
    set({
      isActive: true
    })
  },

  reset: () => {
    set({
      isActive: true,
      hasAcknowledged: false,
      currentStep: 'welcome'
    })
  },

  checkAndActivateSetup: async () => {
    const { hasAcknowledged, isActive } = get()

    // If setup is already active, don't check again
    if (isActive) {
      console.log('[SetupStore] Setup already active, skipping check')
      return
    }

    try {
      // Check backend configuration status
      const response = await apiClient.checkInitialSetup()

      if (response.success && response.data) {
        // PyTauri automatically converts Python snake_case to TypeScript camelCase
        const { needsSetup, hasModels, hasCompletedSetup } = response.data

        console.log('[SetupStore] Initial setup check:', {
          needsSetup,
          hasModels,
          hasCompletedSetup,
          hasAcknowledged,
          isActive
        })

        // Priority 1: If setup is needed (no models), always activate the flow
        // This takes precedence over has_completed_setup to handle cases where
        // user deleted their configuration
        if (needsSetup) {
          console.log('[SetupStore] Configuration needed (no models), activating initial setup flow')
          set({
            isActive: true,
            hasAcknowledged: false,
            currentStep: 'welcome'
          })
          return
        }

        // Priority 2: If user has models, mark as completed
        if (hasModels) {
          console.log('[SetupStore] User has models, marking setup as acknowledged')
          set({
            hasAcknowledged: true,
            isActive: false
          })
        }
      }
    } catch (error) {
      console.error('[SetupStore] Failed to check initial setup:', error)
      // On error, don't force the setup flow - let user access the app
    }
  }
}))
