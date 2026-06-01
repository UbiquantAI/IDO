import { useEffect, useCallback } from 'react'
import { Play, Square, RotateCcw } from 'lucide-react'
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
import { usePomodoroAudio } from '@/hooks/usePomodoroAudio'
import { useClockSync } from '@/lib/clock/clockSync'

interface PomodoroTimerProps {
  userIntent: string
  selectedTodoId: string | null
  onTodoSelect: (todoId: string | null) => void
  onUserIntentChange: (value: string) => void
  onClearTask?: () => void
}

export function PomodoroTimer({
  userIntent,
  selectedTodoId,
  onTodoSelect,
  onUserIntentChange,
  onClearTask
}: PomodoroTimerProps) {
  const { t } = useTranslation()
  const { status, session, error, config, setStatus, setSession, setError, reset, setConfig } = usePomodoroStore()
  const { todos } = useInsightsStore()

  // Initialize notification sounds
  usePomodoroAudio()

  // Initialize clock sync
  useClockSync()

  // Listen for phase switches (work -> break or break -> work)
  usePomodoroPhaseSwitched((payload) => {
    console.log('[Pomodoro] Phase switched:', payload)

    // Handle session completion (from manual end or automatic completion)
    // usePomodoroStateSync handles the state reset, so we just skip API call
    if (payload.new_phase === 'completed') {
      console.log('[Pomodoro] Session completed via phase-switched event')
      return
    }

    // Refresh session data to get updated phase info for work/break phases
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

  // Check for active session on mount
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const result = await getPomodoroStatus()
        if (result.success && result.data) {
          setStatus('active')
          setSession(result.data)
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
          onClearTask?.()
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
  }, [status, setSession, reset, onClearTask])

  const handleStart = useCallback(async () => {
    if (!userIntent.trim() && !selectedTodoId) {
      toast.error(t('pomodoro.error.noIntent'))
      return
    }

    setStatus('active')
    setError(null)

    try {
      // Use userIntent if provided, otherwise use the selected todo's title
      let intentToUse = userIntent.trim()
      if (!intentToUse && selectedTodoId) {
        const selectedTodo = todos.find((todo) => todo.id === selectedTodoId)
        intentToUse = selectedTodo?.title || ''
      }

      const totalDuration =
        (config.workDurationMinutes + config.breakDurationMinutes) * config.totalRounds - config.breakDurationMinutes

      const result = await startPomodoro({
        userIntent: intentToUse,
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
  }, [userIntent, config, selectedTodoId, todos, setStatus, setSession, setError, t])

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
        onClearTask?.()
      } else {
        throw new Error(result.error || 'Failed to end Pomodoro')
      }
    } catch (err: any) {
      console.error('[Pomodoro] Failed to end:', err)
      setError(err.message || String(err))
      toast.error(t('pomodoro.error.endFailed', { error: err.message || String(err) }))
      setStatus('active') // Revert to active
    }
  }, [session, setStatus, setError, reset, onClearTask, t])

  const handleReset = useCallback(() => {
    setConfig({
      workDurationMinutes: 25,
      breakDurationMinutes: 5,
      totalRounds: 2
    })
  }, [setConfig])

  return (
    <div className="flex w-full flex-col">
      {/* Main Card - Unified Vertical Layout */}
      <Card className="border-border/40 from-background via-background to-muted/10 ring-border/5 flex h-full flex-col bg-linear-to-br ring-1 backdrop-blur-sm">
        <CardContent className="flex-1 overflow-y-auto">
          <div className="flex flex-col gap-8">
            {/* Top Section - Task Selection */}
            <div className="w-full">
              <TodoAssociationSelector
                selectedTodoId={selectedTodoId}
                onTodoSelect={onTodoSelect}
                userIntent={userIntent}
                onUserIntentChange={onUserIntentChange}
                disabled={status === 'active'}
              />
            </div>

            {/* Horizontal Divider */}
            <div className="via-border/60 h-px w-full bg-linear-to-r from-transparent to-transparent" />

            {/* Timer & Controls */}
            <div className="flex flex-col items-center gap-6">
              {/* Mode Selector - Only show when idle */}
              {status === 'idle' && (
                <div className="w-full max-w-2xl">
                  <PomodoroModeSelector />
                </div>
              )}

              {/* Timer Display */}
              <div className="w-full max-w-2xl">
                <PomodoroTimerDisplay />
              </div>

              {/* Control Buttons */}
              <div className="flex items-center justify-center gap-3">
                {status === 'idle' ? (
                  <>
                    <Button
                      onClick={handleStart}
                      disabled={!userIntent.trim() && !selectedTodoId}
                      className="gap-2 font-semibold shadow-sm transition-all hover:shadow-md disabled:hover:shadow-sm">
                      <Play className="h-4 w-4" />
                      {t('pomodoro.start')}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={handleReset}
                      className="border-border/50 shadow-sm transition-all hover:shadow-md"
                      title={t('pomodoro.timer.reset')}>
                      <RotateCcw className="h-4 w-4" />
                    </Button>
                  </>
                ) : (
                  <Button
                    onClick={handleEnd}
                    variant="destructive"
                    className="gap-2 font-semibold shadow-sm transition-all hover:shadow-md">
                    <Square className="h-4 w-4" />
                    {t('pomodoro.end')}
                  </Button>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Error Display */}
      {error && (
        <div className="bg-destructive/10 text-destructive border-destructive/20 animate-in fade-in slide-in-from-top-2 mt-6 rounded-2xl border p-4 text-sm shadow-sm duration-300">
          <strong className="font-semibold">{t('pomodoro.error.title')}:</strong> {error}
        </div>
      )}
    </div>
  )
}
