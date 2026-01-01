import { useEffect, useState, useCallback } from 'react'
import { ChevronUp, ChevronDown } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { usePomodoroStore } from '@/lib/stores/pomodoro'
import { cn } from '@/lib/utils'

/**
 * Large centered timer display for Pomodoro
 * Shows MM:SS in a large, prominent font
 * In idle mode: shows config time with arrow adjusters
 * In active mode: shows countdown
 */
export function PomodoroTimerDisplay() {
  const { t } = useTranslation()
  const { session, config, status, setConfig } = usePomodoroStore()
  const [currentTime, setCurrentTime] = useState(Date.now())

  // Update current time every second for real-time calculation
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(Date.now())
    }, 1000)

    return () => clearInterval(interval)
  }, [])

  // Adjust work duration (1 minute increments)
  const adjustWorkDuration = useCallback(
    (delta: number) => {
      const newValue = Math.max(1, Math.min(120, config.workDurationMinutes + delta))
      setConfig({ ...config, workDurationMinutes: newValue })
    },
    [config, setConfig]
  )

  // Adjust break duration (1 minute increments)
  const adjustBreakDuration = useCallback(
    (delta: number) => {
      const newValue = Math.max(1, Math.min(60, config.breakDurationMinutes + delta))
      setConfig({ ...config, breakDurationMinutes: newValue })
    },
    [config, setConfig]
  )

  // Adjust total rounds
  const adjustRounds = useCallback(
    (delta: number) => {
      const newValue = Math.max(1, Math.min(10, config.totalRounds + delta))
      setConfig({ ...config, totalRounds: newValue })
    },
    [config, setConfig]
  )

  // Calculate display time
  let displayMinutes = config.workDurationMinutes
  let displaySeconds = 0

  if (status === 'active' && session) {
    const currentPhase = session.currentPhase || 'work'
    const isWorkPhase = currentPhase === 'work'
    const isCompleted = currentPhase === 'completed'

    const phaseDurationSeconds = isWorkPhase
      ? (session.workDurationMinutes || 25) * 60
      : (session.breakDurationMinutes || 5) * 60

    let remainingSeconds = 0
    if (!isCompleted) {
      const phaseStartTime = session.phaseStartTime ? new Date(session.phaseStartTime).getTime() : null

      if (phaseStartTime) {
        const elapsedSeconds = Math.floor((currentTime - phaseStartTime) / 1000)
        remainingSeconds = Math.max(0, phaseDurationSeconds - elapsedSeconds)
      } else if (session.remainingPhaseSeconds != null) {
        remainingSeconds = session.remainingPhaseSeconds
      } else {
        remainingSeconds = phaseDurationSeconds
      }
    }

    displayMinutes = Math.floor(remainingSeconds / 60)
    displaySeconds = remainingSeconds % 60
  }

  const formattedMinutes = displayMinutes.toString().padStart(2, '0')
  const formattedSeconds = displaySeconds.toString().padStart(2, '0')

  // Determine phase color
  const currentPhase = session?.currentPhase || 'work'
  const isWorkPhase = currentPhase === 'work'

  // Idle mode: show adjustable timer
  if (status === 'idle') {
    return (
      <div className="flex flex-col items-center gap-2 py-2">
        {/* Main time display with adjusters */}
        <div className="flex items-center gap-4">
          {/* Minutes adjuster */}
          <div className="flex flex-col items-center">
            <Button
              variant="ghost"
              size="icon"
              className="hover:bg-muted/50 h-8 w-8"
              onClick={() => adjustWorkDuration(1)}>
              <ChevronUp className="h-5 w-5" />
            </Button>
            <span className="font-mono text-7xl font-bold tabular-nums">{formattedMinutes}</span>
            <Button
              variant="ghost"
              size="icon"
              className="hover:bg-muted/50 h-8 w-8"
              onClick={() => adjustWorkDuration(-1)}>
              <ChevronDown className="h-5 w-5" />
            </Button>
          </div>

          {/* Colon separator */}
          <span className="font-mono text-7xl font-bold">:</span>

          {/* Seconds (fixed at 00 in idle mode) */}
          <div className="flex flex-col items-center">
            <div className="h-8 w-8" /> {/* Spacer for alignment */}
            <span className="text-muted-foreground font-mono text-7xl font-bold tabular-nums">00</span>
            <div className="h-8 w-8" /> {/* Spacer for alignment */}
          </div>
        </div>

        {/* Break time and rounds adjusters */}
        <div className="flex items-center justify-center gap-6">
          {/* Break time adjuster */}
          <div className="flex flex-col items-center gap-1">
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                className="hover:bg-muted/50 h-6 w-6"
                onClick={() => adjustBreakDuration(-1)}>
                <ChevronDown className="h-4 w-4" />
              </Button>
              <span className="text-muted-foreground text-sm tabular-nums">{config.breakDurationMinutes}</span>
              <Button
                variant="ghost"
                size="icon"
                className="hover:bg-muted/50 h-6 w-6"
                onClick={() => adjustBreakDuration(1)}>
                <ChevronUp className="h-4 w-4" />
              </Button>
            </div>
            <span className="text-muted-foreground text-xs">{t('pomodoro.phase.break')}</span>
          </div>

          {/* Separator */}
          <span className="text-muted-foreground/50">|</span>

          {/* Rounds adjuster */}
          <div className="flex flex-col items-center gap-1">
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                className="hover:bg-muted/50 h-6 w-6"
                onClick={() => adjustRounds(-1)}>
                <ChevronDown className="h-4 w-4" />
              </Button>
              <span className="text-muted-foreground text-sm tabular-nums">{config.totalRounds}</span>
              <Button variant="ghost" size="icon" className="hover:bg-muted/50 h-6 w-6" onClick={() => adjustRounds(1)}>
                <ChevronUp className="h-4 w-4" />
              </Button>
            </div>
            <span className="text-muted-foreground text-xs">{t('pomodoro.config.rounds')}</span>
          </div>
        </div>
      </div>
    )
  }

  // Active mode: show countdown
  return (
    <div className="flex items-center justify-center py-2">
      <div
        className={cn(
          'font-mono text-7xl font-bold tracking-tight tabular-nums',
          'transition-colors duration-300',
          isWorkPhase ? 'text-foreground' : 'text-chart-2'
        )}>
        <span>{formattedMinutes}</span>
        <span className="mx-1 animate-pulse">:</span>
        <span>{formattedSeconds}</span>
      </div>
    </div>
  )
}
