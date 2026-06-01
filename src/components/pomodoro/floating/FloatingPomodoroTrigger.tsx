import { Timer } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { usePomodoroStore } from '@/lib/stores/pomodoro'
import { useUIStore } from '@/lib/stores/ui'
import { cn } from '@/lib/utils'

export function FloatingPomodoroTrigger() {
  const { t } = useTranslation()
  const { status, session } = usePomodoroStore()
  const { pomodoroFloatingPanelOpen, togglePomodoroFloatingPanel } = useUIStore()

  // Hide trigger when panel is open
  if (pomodoroFloatingPanelOpen) {
    return null
  }

  const isActive = status === 'active'
  const isBreak = session?.currentPhase === 'break'

  return (
    <button
      onClick={togglePomodoroFloatingPanel}
      className={cn(
        'border-border bg-background fixed top-1/2 right-0 z-40 flex size-12 -translate-y-1/2 items-center justify-center rounded-l-lg border-y border-l shadow-lg transition-all duration-300 hover:w-14 hover:shadow-xl',
        isActive && 'border-primary bg-primary/5 animate-pulse'
      )}
      aria-label={t('pomodoro.floating.open')}
      title={t('pomodoro.floating.open')}>
      {/* Icon */}
      <Timer
        className={cn(
          'text-muted-foreground size-6 transition-colors',
          isActive && 'text-primary',
          isBreak && 'text-chart-2'
        )}
      />
    </button>
  )
}
