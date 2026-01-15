import { createContext, useContext, useEffect, useState } from 'react'
import { useSettingsStore } from '@/lib/stores/settings'

type Theme = 'dark' | 'light' | 'system'
type FontSize = 'small' | 'default' | 'large' | 'extra-large'

type ThemeProviderProps = {
  children: React.ReactNode
  defaultTheme?: Theme
  storageKey?: string
}

type ThemeProviderState = {
  theme: Theme
  fontSize: FontSize
  setTheme: (theme: Theme) => void
  setFontSize: (fontSize: FontSize) => void
}

const initialState: ThemeProviderState = {
  theme: 'system',
  fontSize: 'default',
  setTheme: () => null,
  setFontSize: () => null
}

const ThemeProviderContext = createContext<ThemeProviderState>(initialState)

export function ThemeProvider({
  children,
  defaultTheme = 'system',
  storageKey = 'vite-ui-theme',
  ...props
}: ThemeProviderProps) {
  const [theme, setTheme] = useState<Theme>(() => (localStorage.getItem(storageKey) as Theme) || defaultTheme)
  const settings = useSettingsStore((state) => state.settings)
  const updateFontSize = useSettingsStore((state) => state.updateFontSize)

  useEffect(() => {
    const root = window.document.documentElement

    root.classList.remove('light', 'dark')

    if (theme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'

      root.classList.add(systemTheme)
      return
    }

    root.classList.add(theme)
  }, [theme])

  useEffect(() => {
    const root = window.document.documentElement

    // Apply font size CSS variable
    const fontSizeMap: Record<FontSize, string> = {
      small: '--font-size-small',
      default: '--font-size-default',
      large: '--font-size-large',
      'extra-large': '--font-size-extra-large'
    }

    const fontSizeVar = fontSizeMap[settings.fontSize]
    if (fontSizeVar) {
      const value = getComputedStyle(root).getPropertyValue(fontSizeVar).trim()
      root.style.fontSize = value || '14px'
    }
  }, [settings.fontSize])

  const value = {
    theme,
    fontSize: settings.fontSize,
    setTheme: (theme: Theme) => {
      localStorage.setItem(storageKey, theme)
      setTheme(theme)
    },
    setFontSize: (fontSize: FontSize) => {
      updateFontSize(fontSize)
    }
  }

  return (
    <ThemeProviderContext.Provider {...props} value={value}>
      {children}
    </ThemeProviderContext.Provider>
  )
}

export const useTheme = () => {
  const context = useContext(ThemeProviderContext)

  if (context === undefined) throw new Error('useTheme must be used within a ThemeProvider')

  return context
}
