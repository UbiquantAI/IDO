import { useEffect, useState, useCallback, useMemo } from 'react'
import { ChevronUp, ChevronDown, Clock, Coffee, Timer } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { usePomodoroStore } from '@/lib/stores/pomodoro'
import { cn } from '@/lib/utils'

/**
 * Refined circular timer display for Pomodoro
 * In idle mode: shows config time with elegant adjusters
 * In active mode: shows countdown with circular progress
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

  // Calculate display time and progress
  const { displayMinutes, displaySeconds, progress } = useMemo(() => {
    let minutes = config.workDurationMinutes
    let seconds = 0
    let prog = 0
    let phaseDuration = config.workDurationMinutes * 60

    if (status === 'active' && session) {
      const currentPhase = session.currentPhase || 'work'
      const isWorkPhase = currentPhase === 'work'
      const isCompleted = currentPhase === 'completed'

      phaseDuration = isWorkPhase ? (session.workDurationMinutes || 25) * 60 : (session.breakDurationMinutes || 5) * 60

      let remainingSeconds = 0
      if (!isCompleted) {
        const phaseStartTime = session.phaseStartTime ? new Date(session.phaseStartTime).getTime() : null

        if (phaseStartTime) {
          const elapsedSeconds = Math.floor((currentTime - phaseStartTime) / 1000)
          remainingSeconds = Math.max(0, phaseDuration - elapsedSeconds)
          prog = Math.min(100, (elapsedSeconds / phaseDuration) * 100)
        } else if (session.remainingPhaseSeconds != null) {
          remainingSeconds = session.remainingPhaseSeconds
          prog = Math.min(100, ((phaseDuration - remainingSeconds) / phaseDuration) * 100)
        } else {
          remainingSeconds = phaseDuration
        }
      } else {
        prog = 100
      }

      minutes = Math.floor(remainingSeconds / 60)
      seconds = remainingSeconds % 60
    }

    return {
      displayMinutes: minutes,
      displaySeconds: seconds,
      progress: prog,
      phaseDurationSeconds: phaseDuration
    }
  }, [status, session, config, currentTime])

  const formattedMinutes = displayMinutes.toString().padStart(2, '0')
  const formattedSeconds = displaySeconds.toString().padStart(2, '0')

  // Determine phase color
  const currentPhase = session?.currentPhase || 'work'
  const isWorkPhase = currentPhase === 'work'

  // Circular progress dimensions - compact for better layout
  const size = 180
  const strokeWidth = 6
  const radius = (size - strokeWidth * 2) / 2 // Account for stroke width on both sides
  const circumference = radius * 2 * Math.PI
  const offset = circumference - (progress / 100) * circumference

  // Idle mode: show adjustable timer with circular background
  if (status === 'idle') {
    return (
      <div className="flex flex-col items-center gap-3 py-2">
        {/* Circular timer container */}
        <div className="relative inline-flex items-center justify-center">
          {/* Background ring */}
          <svg width={size} height={size} className="-rotate-90">
            <defs>
              <linearGradient id="idle-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" className="[stop-color:hsl(var(--muted))]" stopOpacity="0.5" />
                <stop offset="100%" className="[stop-color:hsl(var(--muted))]" stopOpacity="0.3" />
              </linearGradient>
            </defs>
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke="url(#idle-gradient)"
              strokeWidth={strokeWidth}
            />
          </svg>

          {/* Center content */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            {/* Main time display with adjusters */}
            <div className="flex items-center gap-1">
              {/* Minutes adjuster */}
              <div className="flex flex-col items-center gap-0.5">
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-muted-foreground hover:text-foreground hover:bg-primary/10 h-7 w-7 rounded-full transition-all duration-200 hover:scale-110"
                  onClick={() => adjustWorkDuration(1)}>
                  <ChevronUp className="h-3.5 w-3.5" />
                </Button>
                <span className="font-mono text-4xl font-bold tracking-tight tabular-nums">{formattedMinutes}</span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-muted-foreground hover:text-foreground hover:bg-primary/10 h-7 w-7 rounded-full transition-all duration-200 hover:scale-110"
                  onClick={() => adjustWorkDuration(-1)}>
                  <ChevronDown className="h-3.5 w-3.5" />
                </Button>
              </div>

              {/* Colon separator */}
              <span className="text-muted-foreground/60 font-mono text-2xl font-light">:</span>

              {/* Seconds (fixed at 00 in idle mode) */}
              <div className="flex flex-col items-center">
                <div className="h-7 w-7" />
                <span className="text-muted-foreground/40 font-mono text-4xl font-bold tracking-tight tabular-nums">
                  00
                </span>
                <div className="h-7 w-7" />
              </div>
            </div>

            {/* Work label with icon */}
            <div className="mt-1.5 flex items-center gap-1">
              <Clock className="text-muted-foreground h-3 w-3" />
              <span className="text-muted-foreground text-xs font-medium">{t('pomodoro.phase.work')}</span>
            </div>
          </div>
        </div>

        {/* Secondary adjusters */}
        <div className="flex items-center justify-center gap-6">
          {/* Break time adjuster */}
          <div className="flex flex-col items-center gap-1.5">
            <div className="bg-muted/40 ring-border/50 hover:bg-muted/60 flex items-center gap-0.5 rounded-full px-1.5 py-0.5 ring-1 backdrop-blur-sm transition-all">
              <Button
                variant="ghost"
                size="icon"
                className="hover:bg-background/80 hover:text-foreground h-6 w-6 rounded-full transition-all"
                onClick={() => adjustBreakDuration(-1)}>
                <ChevronDown className="h-3 w-3" />
              </Button>
              <span className="text-foreground min-w-[2ch] text-center text-sm font-semibold tabular-nums">
                {config.breakDurationMinutes}
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="hover:bg-background/80 hover:text-foreground h-6 w-6 rounded-full transition-all"
                onClick={() => adjustBreakDuration(1)}>
                <ChevronUp className="h-3 w-3" />
              </Button>
            </div>
            <div className="flex items-center gap-1">
              <Coffee className="text-muted-foreground h-3 w-3" />
              <span className="text-muted-foreground text-xs font-medium">{t('pomodoro.phase.break')}</span>
            </div>
          </div>

          {/* Divider */}
          <div className="bg-border/60 h-6 w-px" />

          {/* Rounds adjuster */}
          <div className="flex flex-col items-center gap-1.5">
            <div className="bg-muted/40 ring-border/50 hover:bg-muted/60 flex items-center gap-0.5 rounded-full px-1.5 py-0.5 ring-1 backdrop-blur-sm transition-all">
              <Button
                variant="ghost"
                size="icon"
                className="hover:bg-background/80 hover:text-foreground h-6 w-6 rounded-full transition-all"
                onClick={() => adjustRounds(-1)}>
                <ChevronDown className="h-3 w-3" />
              </Button>
              <span className="text-foreground min-w-[2ch] text-center text-sm font-semibold tabular-nums">
                {config.totalRounds}
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="hover:bg-background/80 hover:text-foreground h-6 w-6 rounded-full transition-all"
                onClick={() => adjustRounds(1)}>
                <ChevronUp className="h-3 w-3" />
              </Button>
            </div>
            <div className="flex items-center gap-1">
              <Timer className="text-muted-foreground h-3 w-3" />
              <span className="text-muted-foreground text-xs font-medium">{t('pomodoro.config.rounds')}</span>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Active mode: show countdown with animated circular progress
  return (
    <div className="flex flex-col items-center gap-3 py-2">
      {/* Circular progress timer */}
      <div className="relative inline-flex items-center justify-center">
        <svg width={size} height={size} className="-rotate-90">
          <defs>
            {/* Work phase gradient */}
            <linearGradient id="work-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" className="[stop-color:hsl(var(--primary))]" stopOpacity="1" />
              <stop offset="100%" className="[stop-color:hsl(var(--primary))]" stopOpacity="0.7" />
            </linearGradient>
            {/* Break phase gradient */}
            <linearGradient id="break-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" className="[stop-color:hsl(var(--chart-2))]" stopOpacity="1" />
              <stop offset="100%" className="[stop-color:hsl(var(--chart-3))]" stopOpacity="0.8" />
            </linearGradient>
            {/* Glow filter */}
            <filter id="glow">
              <feGaussianBlur stdDeviation="1.5" result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
          {/* Background circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            className="stroke-muted"
            strokeWidth={strokeWidth}
            opacity={0.15}
          />
          {/* Progress circle with gradient and glow */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={isWorkPhase ? 'url(#work-gradient)' : 'url(#break-gradient)'}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            filter="url(#glow)"
            className="transition-all duration-1000 ease-linear"
          />
        </svg>

        {/* Center content */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          {/* Phase indicator */}
          <div
            className={cn(
              'mb-2 flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-semibold ring-1 backdrop-blur-sm transition-all duration-300',
              isWorkPhase ? 'bg-primary/15 text-primary ring-primary/20' : 'bg-chart-2/15 text-chart-2 ring-chart-2/20'
            )}>
            {isWorkPhase ? (
              <Clock className="h-3.5 w-3.5 animate-pulse" />
            ) : (
              <Coffee className="h-3.5 w-3.5 animate-pulse" />
            )}
            <span>{isWorkPhase ? t('pomodoro.phase.work') : t('pomodoro.phase.break')}</span>
          </div>

          {/* Time display */}
          <div
            className={cn(
              'font-mono text-5xl font-bold tracking-tight tabular-nums transition-all duration-300',
              isWorkPhase ? 'text-foreground' : 'text-chart-2'
            )}>
            <span>{formattedMinutes}</span>
            <span className="text-muted-foreground/30 mx-0.5 animate-pulse">:</span>
            <span>{formattedSeconds}</span>
          </div>

          {/* Round indicator */}
          {session?.totalRounds && session.totalRounds > 1 && (
            <div className="bg-muted/50 mt-2 flex items-center gap-1 rounded-full px-3 py-1 text-sm font-medium backdrop-blur-sm">
              <span className="text-muted-foreground">
                {t('pomodoro.timer.round')} {session.currentRound || 1}/{session.totalRounds}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Phase duration info */}
      <div className="text-muted-foreground flex items-center gap-1.5 text-center text-sm font-medium">
        <div className={cn('h-1.5 w-1.5 rounded-full', isWorkPhase ? 'bg-primary' : 'bg-chart-2')} />
        <span>
          {isWorkPhase
            ? `${session?.workDurationMinutes || config.workDurationMinutes} ${t('pomodoro.config.minutes')} ${t('pomodoro.phase.work').toLowerCase()}`
            : `${session?.breakDurationMinutes || config.breakDurationMinutes} ${t('pomodoro.config.minutes')} ${t('pomodoro.phase.break').toLowerCase()}`}
        </span>
      </div>
    </div>
  )
}
