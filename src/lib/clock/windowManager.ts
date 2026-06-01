/**
 * Clock window manager - Creates and manages the desktop clock window
 * Reuses the LIVE2D window manager pattern
 */

import { emitTo } from '@tauri-apps/api/event'
import { PhysicalPosition, PhysicalSize, getCurrentWindow } from '@tauri-apps/api/window'
import { WebviewWindow } from '@tauri-apps/api/webviewWindow'

import { isTauri } from '@/lib/utils/tauri'
import { CLOCK_WINDOW_SIZES, CLOCK_WINDOW_MARGIN } from './constants'

const WINDOW_LABEL = 'ido-clock'

// Callback for saving position changes
let onPositionChange: ((x: number, y: number, width: number, height: number) => void) | null = null

export const setOnPositionChange = (
  callback: ((x: number, y: number, width: number, height: number) => void) | null
) => {
  onPositionChange = callback
}

interface ClockState {
  sessionId: string | null
  phase: 'work' | 'break' | 'completed' | null
  remainingSeconds: number
  totalSeconds: number
  currentRound: number
  totalRounds: number
  completedRounds: number
  userIntent: string
  phaseStartTime: string | null
  workDurationMinutes: number
  breakDurationMinutes: number
}

let initializing = false
let currentState: ClockState = {
  sessionId: null,
  phase: null,
  remainingSeconds: 0,
  totalSeconds: 0,
  currentRound: 1,
  totalRounds: 4,
  completedRounds: 0,
  userIntent: '',
  phaseStartTime: null,
  workDurationMinutes: 25,
  breakDurationMinutes: 5
}

interface CustomPosition {
  x?: number
  y?: number
  width?: number
  height?: number
}

const createClockWindow = async (customPosition?: CustomPosition) => {
  const url = import.meta.env.DEV ? '/clock.html' : 'tauri://localhost/clock.html'
  console.log('[Clock] Using URL:', url)

  const defaultSize = CLOCK_WINDOW_SIZES.medium
  const width = customPosition?.width || defaultSize.width
  const height = customPosition?.height || defaultSize.height
  console.log('[Clock] Window size:', { width, height })

  const win = new WebviewWindow(WINDOW_LABEL, {
    url,
    width,
    height,
    minWidth: 120,
    minHeight: 120,
    transparent: true,
    decorations: false,
    shadow: false,
    alwaysOnTop: true,
    resizable: true,
    focus: false,
    skipTaskbar: true
  })
  console.log('[Clock] WebviewWindow created, label:', WINDOW_LABEL)

  try {
    if (customPosition?.x !== undefined && customPosition?.y !== undefined) {
      // Use custom position
      console.log('[Clock] Using custom position:', { x: customPosition.x, y: customPosition.y })
      await win.setPosition(new PhysicalPosition(customPosition.x, customPosition.y))
    } else {
      // Calculate default position relative to main window
      const mainWindow = getCurrentWindow()
      const current = await mainWindow.outerPosition()
      const mainSize = await mainWindow.outerSize()
      const x = current.x + mainSize.width - (width + CLOCK_WINDOW_MARGIN.x)
      const y = current.y + mainSize.height - (height + CLOCK_WINDOW_MARGIN.y)
      console.log('[Clock] Positioning window at:', { x, y })
      await win.setPosition(new PhysicalPosition(x, y))
    }
  } catch (error) {
    console.warn('[Clock] Failed to position window', error)
  }

  win.once('tauri://created', async () => {
    console.log('[Clock] Window created event received')
    // Send initial state to clock window
    await emitTo(WINDOW_LABEL, 'clock-update', currentState)

    // Set up position/size change listeners
    setupPositionListeners(win)
  })

  win.once('tauri://error', (event: any) => {
    console.error('[Clock] Window error:', event)
  })

  return win
}

// Debounce timer for position changes
let positionChangeTimer: ReturnType<typeof setTimeout> | null = null

const setupPositionListeners = (win: WebviewWindow) => {
  // Listen for move events
  win.onMoved(async () => {
    if (!onPositionChange) return

    // Debounce to avoid too many updates
    if (positionChangeTimer) {
      clearTimeout(positionChangeTimer)
    }

    positionChangeTimer = setTimeout(async () => {
      try {
        const pos = await win.outerPosition()
        const size = await win.outerSize()
        console.log('[Clock] Position changed:', { x: pos.x, y: pos.y, width: size.width, height: size.height })
        onPositionChange?.(pos.x, pos.y, size.width, size.height)
      } catch (error) {
        console.warn('[Clock] Failed to get window position:', error)
      }
    }, 300)
  })

  // Listen for resize events
  win.onResized(async () => {
    if (!onPositionChange) return

    // Debounce to avoid too many updates
    if (positionChangeTimer) {
      clearTimeout(positionChangeTimer)
    }

    positionChangeTimer = setTimeout(async () => {
      try {
        const pos = await win.outerPosition()
        const size = await win.outerSize()
        console.log('[Clock] Size changed:', { x: pos.x, y: pos.y, width: size.width, height: size.height })
        onPositionChange?.(pos.x, pos.y, size.width, size.height)
      } catch (error) {
        console.warn('[Clock] Failed to get window size:', error)
      }
    }, 300)
  })
}

export const ensureClockWindow = async (customPosition?: CustomPosition) => {
  if (!isTauri()) {
    console.log('[Clock] Not running in Tauri, skipping window creation')
    return null
  }

  console.log('[Clock] Ensuring clock window exists...', customPosition ? 'with custom position' : '')
  const existing = await WebviewWindow.getByLabel(WINDOW_LABEL)
  if (existing) {
    console.log('[Clock] Clock window already exists')
    try {
      // If custom position is provided, update the existing window position/size
      if (customPosition) {
        if (customPosition.x !== undefined && customPosition.y !== undefined) {
          console.log('[Clock] Updating existing window position:', { x: customPosition.x, y: customPosition.y })
          await existing.setPosition(new PhysicalPosition(customPosition.x, customPosition.y))
        }
        if (customPosition.width !== undefined && customPosition.height !== undefined) {
          console.log('[Clock] Updating existing window size:', {
            width: customPosition.width,
            height: customPosition.height
          })
          await existing.setSize(new PhysicalSize(customPosition.width, customPosition.height))
        }
      }

      await existing.show()
      // Send current state to existing window
      await emitTo(WINDOW_LABEL, 'clock-update', currentState)
      // Set up listeners for existing window too
      setupPositionListeners(existing)
    } catch (error) {
      console.warn('[Clock] Unable to show clock window', error)
    }
    return existing
  }

  if (initializing) {
    console.log('[Clock] Clock window is being initialized, waiting...')
    return await WebviewWindow.getByLabel(WINDOW_LABEL)
  }

  console.log('[Clock] Creating new clock window...')
  initializing = true
  try {
    const win = await createClockWindow(customPosition)
    console.log('[Clock] Clock window created successfully')
    return win
  } catch (error) {
    console.error('[Clock] Failed to create clock window:', error)
    throw error
  } finally {
    initializing = false
  }
}

export const closeClockWindow = async () => {
  if (!isTauri()) return
  const existing = await WebviewWindow.getByLabel(WINDOW_LABEL)
  if (existing) {
    try {
      await existing.close()
    } catch (error) {
      console.warn('[Clock] Failed to close window', error)
    }
  }
}

export const syncClockWindow = async (settings: { enabled: boolean }) => {
  if (!isTauri()) return
  if (settings.enabled) {
    await ensureClockWindow()
  } else {
    await closeClockWindow()
  }
}

export const updateClockState = async (state: Partial<ClockState>) => {
  if (!isTauri()) return

  currentState = { ...currentState, ...state }

  try {
    const existing = await WebviewWindow.getByLabel(WINDOW_LABEL)
    if (existing) {
      await emitTo(WINDOW_LABEL, 'clock-update', currentState)
    }
  } catch (error) {
    console.warn('[Clock] Failed to send state update:', error)
  }
}

export const hideClockWindow = async () => {
  if (!isTauri()) return
  const existing = await WebviewWindow.getByLabel(WINDOW_LABEL)
  if (existing) {
    try {
      await existing.hide()
    } catch (error) {
      console.warn('[Clock] Failed to hide window:', error)
    }
  }
}

export const showClockWindow = async () => {
  if (!isTauri()) return
  const existing = await WebviewWindow.getByLabel(WINDOW_LABEL)
  if (existing) {
    try {
      await existing.show()
    } catch (error) {
      console.warn('[Clock] Failed to show window:', error)
    }
  }
}

export const setClockPosition = async (
  position: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left',
  size: 'small' | 'medium' | 'large' = 'medium'
) => {
  if (!isTauri()) return

  try {
    const existing = await WebviewWindow.getByLabel(WINDOW_LABEL)
    if (!existing) return

    const mainWindow = getCurrentWindow()
    const current = await mainWindow.outerPosition()
    const mainSize = await mainWindow.outerSize()
    const windowSize = CLOCK_WINDOW_SIZES[size]

    let x = current.x
    let y = current.y

    switch (position) {
      case 'bottom-right':
        x = current.x + mainSize.width - (windowSize.width + CLOCK_WINDOW_MARGIN.x)
        y = current.y + mainSize.height - (windowSize.height + CLOCK_WINDOW_MARGIN.y)
        break
      case 'bottom-left':
        x = current.x + CLOCK_WINDOW_MARGIN.x
        y = current.y + mainSize.height - (windowSize.height + CLOCK_WINDOW_MARGIN.y)
        break
      case 'top-right':
        x = current.x + mainSize.width - (windowSize.width + CLOCK_WINDOW_MARGIN.x)
        y = current.y + CLOCK_WINDOW_MARGIN.y
        break
      case 'top-left':
        x = current.x + CLOCK_WINDOW_MARGIN.x
        y = current.y + CLOCK_WINDOW_MARGIN.y
        break
    }

    await existing.setPosition(new PhysicalPosition(x, y))
    await existing.setSize(windowSize as any)
  } catch (error) {
    console.warn('[Clock] Failed to set position:', error)
  }
}

export const setClockCustomPosition = async (x: number, y: number, width: number, height: number) => {
  if (!isTauri()) return

  try {
    const existing = await WebviewWindow.getByLabel(WINDOW_LABEL)
    if (!existing) return

    console.log('[Clock] Setting custom position:', { x, y, width, height })
    await existing.setPosition(new PhysicalPosition(x, y))
    await existing.setSize(new PhysicalSize(width, height))
  } catch (error) {
    console.warn('[Clock] Failed to set custom position:', error)
  }
}
