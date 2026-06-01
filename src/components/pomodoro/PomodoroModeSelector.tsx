import { useTranslation } from 'react-i18next'
import { Clock, Zap, Timer, Brain } from 'lucide-react'

import { usePomodoroStore } from '@/lib/stores/pomodoro'
import { cn } from '@/lib/utils'

// Mode configurations with icons and descriptions
const MODE_CONFIGS = {
  classic: {
    icon: Clock,
    workMinutes: 25,
    breakMinutes: 5,
    rounds: 2
  },
  deep: {
    icon: Brain,
    workMinutes: 50,
    breakMinutes: 10,
    rounds: 2
  },
  quick: {
    icon: Zap,
    workMinutes: 15,
    breakMinutes: 3,
    rounds: 2
  },
  focus: {
    icon: Timer,
    workMinutes: 90,
    breakMinutes: 20,
    rounds: 1
  }
} as const

type ModeId = keyof typeof MODE_CONFIGS

export function PomodoroModeSelector() {
  const { t } = useTranslation()
  const { config, setConfig } = usePomodoroStore()

  const handleModeClick = (modeId: ModeId) => {
    const modeConfig = MODE_CONFIGS[modeId]
    setConfig({
      workDurationMinutes: modeConfig.workMinutes,
      breakDurationMinutes: modeConfig.breakMinutes,
      totalRounds: modeConfig.rounds
    })
  }

  // Check if current config matches a mode
  const getActiveMode = (): ModeId | null => {
    for (const [modeId, modeConfig] of Object.entries(MODE_CONFIGS)) {
      if (
        config.workDurationMinutes === modeConfig.workMinutes &&
        config.breakDurationMinutes === modeConfig.breakMinutes &&
        config.totalRounds === modeConfig.rounds
      ) {
        return modeId as ModeId
      }
    }
    return null
  }

  const activeMode = getActiveMode()
  const modes: ModeId[] = ['classic', 'deep', 'quick', 'focus']

  return (
    <div className="flex flex-wrap items-center justify-center gap-2">
      {modes.map((modeId) => {
        const modeConfig = MODE_CONFIGS[modeId]
        const Icon = modeConfig.icon
        const isActive = activeMode === modeId

        return (
          <button
            key={modeId}
            onClick={() => handleModeClick(modeId)}
            className={cn(
              'group flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-semibold transition-all duration-300',
              'focus-visible:ring-ring focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none',
              isActive
                ? 'bg-primary text-primary-foreground ring-primary/20 scale-105 ring-2'
                : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground ring-border/40 bg-background/50 ring-1 backdrop-blur-sm hover:scale-105'
            )}>
            <Icon
              className={cn(
                'h-3.5 w-3.5 transition-all duration-300',
                isActive ? 'scale-110 rotate-6' : 'group-hover:scale-110 group-hover:rotate-6'
              )}
            />
            <span className="transition-all duration-300">{t(`pomodoro.modes.${modeId}`)}</span>
          </button>
        )
      })}
    </div>
  )
}
