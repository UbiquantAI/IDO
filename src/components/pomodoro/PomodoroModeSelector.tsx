import { useTranslation } from 'react-i18next'
import { Clock, Zap, Timer, Brain } from 'lucide-react'

import { usePomodoroStore } from '@/lib/stores/pomodoro'
import { cn } from '@/lib/utils'

// Mode configurations with icons
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
  const { setConfig } = usePomodoroStore()

  const handleModeClick = (modeId: ModeId) => {
    const modeConfig = MODE_CONFIGS[modeId]
    setConfig({
      workDurationMinutes: modeConfig.workMinutes,
      breakDurationMinutes: modeConfig.breakMinutes,
      totalRounds: modeConfig.rounds
    })
  }

  const modes: ModeId[] = ['classic', 'deep', 'quick', 'focus']

  return (
    <div className="grid grid-cols-4 gap-2">
      {modes.map((modeId) => {
        const modeConfig = MODE_CONFIGS[modeId]
        const Icon = modeConfig.icon

        return (
          <button
            key={modeId}
            onClick={() => handleModeClick(modeId)}
            className={cn(
              'flex flex-col items-center gap-1.5 rounded-lg px-3 py-3 transition-all',
              'border-border bg-background border-2',
              'hover:border-primary hover:bg-primary/5',
              'active:scale-95'
            )}>
            <Icon className="h-5 w-5" />
            <span className="text-sm font-medium">{t(`pomodoro.modes.${modeId}`)}</span>
          </button>
        )
      })}
    </div>
  )
}
