// Settings-related type definitions
// Note: LLM model config moved to the multi-model management system
// See src/lib/types/models.ts and src/lib/stores/models.ts

export interface DatabaseSettings {
  path?: string
}

export interface ScreenshotSettings {
  savePath?: string
}

// Multi-monitor info
export interface MonitorInfo {
  index: number
  name: string
  width: number
  height: number
  left: number
  top: number
  is_primary: boolean
  resolution: string
}

// Screen selection settings
export interface ScreenSetting {
  id?: number
  monitor_index: number
  monitor_name: string
  is_enabled: boolean
  resolution: string
  is_primary: boolean
  created_at?: string
  updated_at?: string
}

export interface FriendlyChatSettings {
  enabled: boolean
  interval: number // minutes (5-120)
  dataWindow: number // minutes (5-120)
  enableSystemNotification: boolean
  enableLive2dDisplay: boolean
}

export interface VoiceSettings {
  enabled: boolean
  volume: number
  soundTheme: '8bit' | '16bit' | 'custom'
  customSounds?: {
    workComplete?: string
    breakComplete?: string
    sessionComplete?: string
  }
}

export interface ClockSettings {
  enabled: boolean
  position: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left'
  size: 'small' | 'medium' | 'large'
  // Custom position (absolute screen coordinates)
  customX?: number
  customY?: number
  customWidth?: number
  customHeight?: number
  useCustomPosition?: boolean
}

export interface AppSettings {
  database?: DatabaseSettings
  screenshot?: ScreenshotSettings
  theme: 'light' | 'dark' | 'system'
  language: 'zh-CN' | 'en-US'
  fontSize: 'small' | 'default' | 'large' | 'extra-large'
  friendlyChat?: FriendlyChatSettings
  voice?: VoiceSettings
  clock?: ClockSettings
}
