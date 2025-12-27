import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { CheckCircle2, Clock, Coffee } from 'lucide-react'

import { CircularProgress } from '@/components/pomodoro/CircularProgress'
import { usePomodoroStore } from '@/lib/stores/pomodoro'
import { cn } from '@/lib/utils'

/**
 * Dual-ring circular progress display for Pomodoro sessions
 * - Outer ring: Overall session progress (completed rounds / total rounds)
 * - Inner ring: Current phase progress (elapsed time / phase duration)
 * - Center: Round info and phase icon
 */
export function CircularRoundProgress() {
  const { t } = useTranslation()
  const { session } = usePomodoroStore()
  const [currentTime, setCurrentTime] = useState(Date.now())

  // Update current time every second for real-time progress calculation
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(Date.now())
    }, 1000)

    return () => clearInterval(interval)
  }, [])

  if (!session) {
    return null
  }

  const currentRound = session.currentRound || 1
  const totalRounds = session.totalRounds || 2
  const completedRounds = session.completedRounds || 0
  const currentPhase = session.currentPhase || 'work'

  const isWorkPhase = currentPhase === 'work'
  const isBreakPhase = currentPhase === 'break'
  const isCompleted = currentPhase === 'completed'

  // Overall session progress (0-100)
  const overallProgress = (completedRounds / totalRounds) * 100

  // Calculate current phase progress (0-100)
  let phaseProgress = 0
  if (!isCompleted) {
    const phaseDurationSeconds = isWorkPhase
      ? (session.workDurationMinutes || 25) * 60
      : (session.breakDurationMinutes || 5) * 60

    const phaseStartTime = session.phaseStartTime ? new Date(session.phaseStartTime).getTime() : null

    if (phaseStartTime) {
      const elapsedSeconds = Math.floor((currentTime - phaseStartTime) / 1000)
      phaseProgress = Math.min(100, (elapsedSeconds / phaseDurationSeconds) * 100)
    }
  } else {
    phaseProgress = 100
  }

  // Phase-specific colors
  const phaseColor = isWorkPhase
    ? 'hsl(var(--primary))'
    : isBreakPhase
      ? 'hsl(var(--chart-2))'
      : 'hsl(var(--muted-foreground))'

  const phaseIconColor = isWorkPhase ? 'text-primary' : isBreakPhase ? 'text-chart-2' : 'text-muted-foreground'

  const PhaseIcon = isWorkPhase ? Clock : isBreakPhase ? Coffee : CheckCircle2

  // Hide outer ring if only one round
  const showOuterRing = totalRounds > 1

  return (
    <div className="flex items-center justify-center">
      <div className="relative">
        {/* Outer ring: Overall session progress */}
        {showOuterRing && (
          <CircularProgress
            progress={overallProgress}
            size={180}
            strokeWidth={5}
            color="hsl(var(--muted-foreground))"
            className="opacity-40">
            <div className="pointer-events-none" />
          </CircularProgress>
        )}

        {/* Inner ring: Current phase progress */}
        <div className={cn('absolute inset-0 flex items-center justify-center', showOuterRing && 'p-3')}>
          <CircularProgress
            progress={phaseProgress}
            size={showOuterRing ? 148 : 180}
            strokeWidth={8}
            color={phaseColor}>
            {/* Center content */}
            <div className="flex flex-col items-center justify-center space-y-1.5">
              {/* Current round number */}
              <div className="text-center">
                <div className="text-3xl leading-none font-bold">{isCompleted ? '✓' : currentRound}</div>
                {!isCompleted && <div className="text-muted-foreground mt-0.5 text-xs">of {totalRounds}</div>}
              </div>

              {/* Phase icon */}
              <div
                className={cn('rounded-full p-1.5', isWorkPhase && 'bg-primary/10', isBreakPhase && 'bg-chart-2/10')}>
                <PhaseIcon className={cn('h-4 w-4', phaseIconColor)} />
              </div>

              {/* Completed count */}
              {!isCompleted && (
                <div className="text-muted-foreground text-xs">
                  {completedRounds} {t('pomodoro.progress.roundsComplete')}
                </div>
              )}

              {/* Completion message */}
              {isCompleted && (
                <div className="text-center">
                  <div className="text-sm font-semibold">{t('pomodoro.progress.completed')}</div>
                  <div className="text-muted-foreground text-xs">
                    {completedRounds}/{totalRounds} {t('pomodoro.progress.roundsComplete')}
                  </div>
                </div>
              )}
            </div>
          </CircularProgress>
        </div>
      </div>
    </div>
  )
}
