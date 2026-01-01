import { useState, useEffect, useCallback } from 'react'
import { Play, Square, RotateCcw, Clock, Coffee } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { toast } from 'sonner'
import { startPomodoro, endPomodoro, getPomodoroStatus } from '@/lib/client/apiClient'
import { usePomodoroStore } from '@/lib/stores/pomodoro'
import { useInsightsStore } from '@/lib/stores/insights'
import { usePomodoroPhaseSwitched } from '@/hooks/useTauriEvents'
import { TodoAssociationSelector } from './TodoAssociationSelector'
import { PomodoroTimerDisplay } from './PomodoroTimerDisplay'
import { PomodoroModeSelector } from './PomodoroModeSelector'
import { PomodoroStats } from './PomodoroStats'
import { cn } from '@/lib/utils'

export function PomodoroTimer() {
  const { t } = useTranslation()
  const { status, session, error, config, setStatus, setSession, setError, reset, setConfig } = usePomodoroStore()
  const { todos } = useInsightsStore()

  const [userIntent, setUserIntent] = useState('')
  const [selectedTodoId, setSelectedTodoId] = useState<string | null>(null)

  // Listen for phase switches (work -> break or break -> work)
  usePomodoroPhaseSwitched((payload) => {
    console.log('[Pomodoro] Phase switched:', payload)

    // Refresh session data to get updated phase info
    getPomodoroStatus()
      .then((result) => {
        if (result.success && result.data) {
          setSession(result.data)

          // Show toast notification
          const phaseText = payload.new_phase === 'work' ? t('pomodoro.phase.work') : t('pomodoro.phase.break')
          toast.info(
            t('pomodoro.phaseSwitch.notification', {
              phase: phaseText,
              round: payload.current_round,
              total: payload.total_rounds
            }),
            { duration: 3000 }
          )
        }
      })
      .catch((err) => {
        console.error('[Pomodoro] Failed to refresh session after phase switch:', err)
      })
  })

  // Auto-fill userIntent when todo is selected (only when idle)
  useEffect(() => {
    // Don't auto-fill when session is active - preserve session data
    if (status === 'active') return

    if (selectedTodoId) {
      const selectedTodo = todos.find((todo) => todo.id === selectedTodoId)
      if (selectedTodo) {
        setUserIntent(selectedTodo.title)
      }
    } else {
      // Clear userIntent when todo is deselected
      setUserIntent('')
    }
  }, [selectedTodoId, todos, status])

  // Sync local state with session data when session changes
  useEffect(() => {
    if (session && status === 'active') {
      // Restore local state from session data
      if (session.associatedTodoId) {
        setSelectedTodoId(session.associatedTodoId)
      }
      if (session.userIntent) {
        setUserIntent(session.userIntent)
      }
    }
  }, [session, status])

  // Check for active session on mount
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const result = await getPomodoroStatus()
        if (result.success && result.data) {
          setStatus('active')
          setSession(result.data)
          // Restore local state from session
          if (result.data.associatedTodoId) {
            setSelectedTodoId(result.data.associatedTodoId)
          }
          if (result.data.userIntent) {
            setUserIntent(result.data.userIntent)
          }
        }
      } catch (err) {
        console.error('[Pomodoro] Failed to check status:', err)
      }
    }

    checkStatus()
  }, [setStatus, setSession])

  // Poll for status updates when Pomodoro is active
  useEffect(() => {
    if (status !== 'active') {
      return
    }

    // Immediately poll on mount/activation
    const pollStatus = async () => {
      try {
        console.log('[PomodoroTimer] Polling status...')
        const result = await getPomodoroStatus()
        console.log('[PomodoroTimer] Poll result:', {
          success: result.success,
          hasData: !!result.data,
          remainingPhaseSeconds: result.data?.remainingPhaseSeconds,
          sessionId: result.data?.sessionId
        })
        if (result.success && result.data) {
          setSession(result.data)
        } else {
          // Session ended on backend
          console.log('[PomodoroTimer] Session ended, resetting')
          reset()
        }
      } catch (err) {
        console.error('[Pomodoro] Failed to poll status:', err)
      }
    }

    pollStatus()

    // Poll every 3 seconds to sync with backend
    const pollInterval = setInterval(pollStatus, 3000)

    // Re-sync when page becomes visible (fixes issue when switching tabs/pages)
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        console.log('[Pomodoro] Page visible, triggering immediate poll')
        pollStatus()
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      clearInterval(pollInterval)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [status, setSession, reset])

  const handleStart = useCallback(async () => {
    if (!userIntent.trim()) {
      toast.error(t('pomodoro.error.noIntent'))
      return
    }

    setStatus('active')
    setError(null)

    try {
      const totalDuration =
        (config.workDurationMinutes + config.breakDurationMinutes) * config.totalRounds - config.breakDurationMinutes

      const result = await startPomodoro({
        userIntent: userIntent.trim(),
        durationMinutes: totalDuration,
        workDurationMinutes: config.workDurationMinutes,
        breakDurationMinutes: config.breakDurationMinutes,
        totalRounds: config.totalRounds,
        associatedTodoId: selectedTodoId || undefined
      })

      if (result.success && result.data) {
        setSession(result.data)
        toast.success(t('pomodoro.started'))
      } else {
        throw new Error(result.error || 'Failed to start Pomodoro')
      }
    } catch (err: any) {
      console.error('[Pomodoro] Failed to start:', err)
      setError(err.message || String(err))
      toast.error(t('pomodoro.error.startFailed', { error: err.message || String(err) }))
      setStatus('idle')
    }
  }, [userIntent, config, selectedTodoId, setStatus, setSession, setError, t])

  const handleEnd = useCallback(async () => {
    if (!session) return

    setStatus('ending')
    setError(null)

    try {
      const result = await endPomodoro({
        status: 'completed'
      })

      if (result.success && result.data) {
        const { rawRecordsCount, message } = result.data

        if (message) {
          toast.info(message)
        } else {
          // Show success message and immediately reset to idle
          const recordCount = rawRecordsCount ?? 0
          toast.success(t('pomodoro.ended', { count: recordCount }))

          // If there are records, show background processing info
          if (recordCount > 0) {
            toast.info(t('pomodoro.processing.background'))
          }
        }

        // Immediately reset to idle state (don't wait for processing)
        reset()
        // Clear local state
        setUserIntent('')
        setSelectedTodoId(null)
      } else {
        throw new Error(result.error || 'Failed to end Pomodoro')
      }
    } catch (err: any) {
      console.error('[Pomodoro] Failed to end:', err)
      setError(err.message || String(err))
      toast.error(t('pomodoro.error.endFailed', { error: err.message || String(err) }))
      setStatus('active') // Revert to active
    }
  }, [session, setStatus, setError, reset, t])

  const handleReset = useCallback(() => {
    setConfig({
      workDurationMinutes: 25,
      breakDurationMinutes: 5,
      totalRounds: 2
    })
  }, [setConfig])

  // Get current phase info for display
  const currentPhase = session?.currentPhase || 'work'
  const isWorkPhase = currentPhase === 'work'

  return (
    <div className="flex w-full flex-col gap-4">
      {/* Task Selector Card */}
      <Card className="border-border">
        <CardContent className="py-4">
          <TodoAssociationSelector
            selectedTodoId={selectedTodoId}
            onTodoSelect={setSelectedTodoId}
            userIntent={userIntent}
            onUserIntentChange={setUserIntent}
            disabled={status === 'active'}
          />
        </CardContent>
      </Card>

      {/* Main Timer Card */}
      <Card className="bg-background">
        <CardContent className="space-y-4 py-4">
          {/* Mode Selector Tabs - Only show when idle */}
          {status === 'idle' && <PomodoroModeSelector />}

          {/* Phase Indicator - Only show when active */}
          {status === 'active' && session && (
            <div className="flex justify-center">
              <div
                className={cn(
                  'flex items-center gap-2 rounded-full px-4 py-1.5',
                  isWorkPhase ? 'bg-primary text-primary-foreground' : 'bg-chart-2 text-white'
                )}>
                {isWorkPhase ? <Clock className="h-4 w-4" /> : <Coffee className="h-4 w-4" />}
                <span className="text-sm font-medium">
                  {isWorkPhase ? t('pomodoro.phase.work') : t('pomodoro.phase.break')}
                  {t('pomodoro.timer.inProgress')}
                </span>
              </div>
            </div>
          )}

          {/* Timer Display with adjusters (idle) or countdown (active) */}
          <PomodoroTimerDisplay />

          {/* Phase Duration Info - Only when active */}
          {status === 'active' && session && (
            <div className="text-muted-foreground text-center text-sm">
              {isWorkPhase
                ? `${session.workDurationMinutes || config.workDurationMinutes} ${t('pomodoro.config.minutes')} ${t('pomodoro.phase.work').toLowerCase()}`
                : `${session.breakDurationMinutes || config.breakDurationMinutes} ${t('pomodoro.config.minutes')} ${t('pomodoro.phase.break').toLowerCase()}`}
              {session.totalRounds && session.totalRounds > 1 && (
                <span className="text-muted-foreground/70">
                  {' '}
                  · {t('pomodoro.timer.round')} {session.currentRound || 1}/{session.totalRounds}
                </span>
              )}
            </div>
          )}

          {/* Progress Bar */}
          <div className="bg-muted mx-auto h-1.5 w-full max-w-md overflow-hidden rounded-full">
            {status === 'active' && session ? (
              <ProgressBar session={session} />
            ) : (
              <div className="bg-primary h-full w-0 transition-all duration-300" />
            )}
          </div>

          {/* Control Buttons */}
          <div className="flex items-center justify-center gap-3">
            {status === 'idle' ? (
              <>
                <Button onClick={handleStart} disabled={!userIntent.trim()} className="gap-2 px-8" size="lg">
                  <Play className="h-5 w-5" />
                  {t('pomodoro.start')}
                </Button>
                <Button variant="outline" onClick={handleReset} className="gap-2" size="lg">
                  <RotateCcw className="h-4 w-4" />
                  {t('pomodoro.timer.reset')}
                </Button>
              </>
            ) : (
              <Button onClick={handleEnd} variant="destructive" className="gap-2 px-8" size="lg">
                <Square className="h-5 w-5" />
                {t('pomodoro.end')}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Statistics Card */}
      <PomodoroStats />

      {error && (
        <div className="bg-destructive/10 text-destructive rounded-md p-3 text-sm">
          <strong>{t('pomodoro.error.title')}:</strong> {error}
        </div>
      )}
    </div>
  )
}

// Progress bar component
function ProgressBar({ session }: { session: any }) {
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    const updateProgress = () => {
      const currentPhase = session.currentPhase || 'work'
      const isWorkPhase = currentPhase === 'work'
      const phaseDurationSeconds = isWorkPhase
        ? (session.workDurationMinutes || 25) * 60
        : (session.breakDurationMinutes || 5) * 60

      const phaseStartTime = session.phaseStartTime ? new Date(session.phaseStartTime).getTime() : null

      if (phaseStartTime) {
        const elapsedSeconds = Math.floor((Date.now() - phaseStartTime) / 1000)
        const newProgress = Math.min(100, (elapsedSeconds / phaseDurationSeconds) * 100)
        setProgress(newProgress)
      }
    }

    updateProgress()
    const interval = setInterval(updateProgress, 1000)
    return () => clearInterval(interval)
  }, [session])

  const currentPhase = session.currentPhase || 'work'
  const isWorkPhase = currentPhase === 'work'

  return (
    <div
      className={cn('h-full transition-all duration-1000', isWorkPhase ? 'bg-primary' : 'bg-chart-2')}
      style={{ width: `${progress}%` }}
    />
  )
}
