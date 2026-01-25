import { create } from 'zustand'
import type {
  AppSettings,
  DatabaseSettings,
  ScreenshotSettings,
  VoiceSettings,
  ClockSettings
} from '@/lib/types/settings'
import * as apiClient from '@/lib/client/apiClient'

interface SettingsState {
  settings: AppSettings
  loading: boolean
  error: string | null

  // Actions
  fetchSettings: () => Promise<void>
  updateDatabaseSettings: (database: Partial<DatabaseSettings>) => Promise<void>
  updateScreenshotSettings: (screenshot: Partial<ScreenshotSettings>) => Promise<void>
  updateTheme: (theme: 'light' | 'dark' | 'system') => void
  updateLanguage: (language: 'zh-CN' | 'en-US') => Promise<void>
  updateFontSize: (fontSize: 'small' | 'default' | 'large' | 'extra-large') => Promise<void>
  updateVoiceSettings: (voice: Partial<VoiceSettings>) => Promise<void>
  updateClockSettings: (clock: Partial<ClockSettings>) => Promise<void>
}

const defaultSettings: AppSettings = {
  database: {
    path: ''
  },
  screenshot: {
    savePath: ''
  },
  theme: 'system',
  language: 'zh-CN',
  fontSize: 'default',
  voice: {
    enabled: true,
    volume: 0.8,
    soundTheme: '8bit'
  },
  clock: {
    enabled: true,
    position: 'bottom-right',
    size: 'medium',
    useCustomPosition: false
  }
}

export const useSettingsStore = create<SettingsState>()((set, get) => ({
  settings: defaultSettings,
  loading: false,
  error: null,

  fetchSettings: async () => {
    set({ loading: true, error: null })
    try {
      const response = await apiClient.getSettingsInfo(undefined)
      if (response && response.data) {
        const data = response.data as any
        const { database, screenshot, fontSize, voice, clock } = data
        if (database || screenshot || fontSize || voice || clock) {
          set((state) => ({
            settings: {
              ...state.settings,
              ...(database && { database: { path: database.path } }),
              ...(screenshot && { screenshot: { savePath: screenshot.savePath } }),
              ...(fontSize && { fontSize }),
              ...(voice && {
                voice: {
                  enabled: voice.enabled,
                  volume: voice.volume,
                  soundTheme:
                    voice.soundTheme || voice.language === 'zh-CN' || voice.language === 'en-US'
                      ? '8bit'
                      : voice.soundTheme || '8bit',
                  customSounds: voice.customSounds
                }
              }),
              ...(clock && {
                clock: {
                  enabled: clock.enabled,
                  position: clock.position,
                  size: clock.size,
                  customX: clock.customX,
                  customY: clock.customY,
                  customWidth: clock.customWidth,
                  customHeight: clock.customHeight,
                  useCustomPosition: clock.useCustomPosition
                }
              })
            },
            loading: false,
            error: null
          }))
        } else {
          set({ loading: false, error: null })
        }
      } else {
        set({ loading: false, error: null })
      }
    } catch (error) {
      console.error('Failed to fetch settings:', error)
      set({ error: (error as Error).message, loading: false })
    }
  },

  updateDatabaseSettings: async (database) => {
    set({ loading: true, error: null })
    try {
      const state = get()
      const fullDatabase = { ...(state.settings.database || {}), ...database }
      await apiClient.updateSettings({
        databasePath: fullDatabase.path || null
      } as any)
      set({
        settings: {
          ...state.settings,
          database: fullDatabase as DatabaseSettings
        },
        loading: false,
        error: null
      })
    } catch (error) {
      console.error('Failed to update database settings:', error)
      set({ error: (error as Error).message, loading: false })
    }
  },

  updateScreenshotSettings: async (screenshot) => {
    set({ loading: true, error: null })
    try {
      const state = get()
      const fullScreenshot = { ...(state.settings.screenshot || {}), ...screenshot }
      await apiClient.updateSettings({
        screenshotSavePath: fullScreenshot.savePath || null
      } as any)
      set({
        settings: {
          ...state.settings,
          screenshot: fullScreenshot as ScreenshotSettings
        },
        loading: false,
        error: null
      })
    } catch (error) {
      console.error('Failed to update screenshot settings:', error)
      set({ error: (error as Error).message, loading: false })
    }
  },

  updateTheme: (theme) =>
    set((state) => ({
      settings: { ...state.settings, theme }
    })),

  updateLanguage: async (language) => {
    // Update frontend state immediately for better UX
    set((state) => ({
      settings: { ...state.settings, language }
    }))

    try {
      // Map frontend language codes to backend language codes
      const backendLanguage = language === 'zh-CN' ? 'zh' : 'en'
      await apiClient.updateSettings({
        language: backendLanguage
      } as any)
      console.log(`✓ Backend language updated to: ${backendLanguage}`)
    } catch (error) {
      console.error('Failed to update backend language:', error)
      // Rollback frontend state on error
      const currentState = get()
      set((state) => ({
        settings: { ...state.settings, language: currentState.settings.language }
      }))
    }
  },

  updateFontSize: async (fontSize) => {
    // Update frontend state immediately for better UX
    set((state) => ({
      settings: { ...state.settings, fontSize }
    }))

    try {
      await apiClient.updateSettings({
        fontSize
      } as any)
      console.log(`✓ Backend font size updated to: ${fontSize}`)
    } catch (error) {
      console.error('Failed to update backend font size:', error)
      // Rollback frontend state on error
      const currentState = get()
      set((state) => ({
        settings: { ...state.settings, fontSize: currentState.settings.fontSize }
      }))
    }
  },

  updateVoiceSettings: async (voice) => {
    set({ loading: true, error: null })
    try {
      const state = get()
      const fullVoice = { ...(state.settings.voice || {}), ...voice }
      await apiClient.updateSettings({
        voiceEnabled: fullVoice.enabled,
        voiceVolume: fullVoice.volume,
        voiceSoundTheme: fullVoice.soundTheme,
        voiceCustomSounds: fullVoice.customSounds || null
      } as any)
      set({
        settings: {
          ...state.settings,
          voice: fullVoice as VoiceSettings
        },
        loading: false,
        error: null
      })
      console.log('✓ Notification sound settings updated:', fullVoice)
    } catch (error) {
      console.error('Failed to update notification sound settings:', error)
      set({ error: (error as Error).message, loading: false })
    }
  },

  updateClockSettings: async (clock) => {
    const state = get()
    const fullClock = { ...(state.settings.clock || {}), ...clock }

    // Update local state immediately for better UX
    set({
      settings: {
        ...state.settings,
        clock: fullClock as ClockSettings
      }
    })

    try {
      await apiClient.updateSettings({
        clockEnabled: fullClock.enabled,
        clockPosition: fullClock.position,
        clockSize: fullClock.size,
        clockCustomX: fullClock.customX,
        clockCustomY: fullClock.customY,
        clockCustomWidth: fullClock.customWidth,
        clockCustomHeight: fullClock.customHeight,
        clockUseCustomPosition: fullClock.useCustomPosition
      } as any)
      console.log('✓ Clock settings updated:', fullClock)
    } catch (error) {
      console.error('Failed to update clock settings:', error)
      // Rollback on error
      set({
        settings: {
          ...get().settings,
          clock: state.settings.clock
        },
        error: (error as Error).message
      })
    }
  }
}))
