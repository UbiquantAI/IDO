import { useState, useEffect, useCallback } from 'react'
import { Clock, Play, Square, ChevronDown, ChevronUp, Coffee, Settings } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'
import { startPomodoro, endPomodoro, getPomodoroStatus } from '@/lib/client/apiClient'
import { usePomodoroStore } from '@/lib/stores/pomodoro'
import { useInsightsStore } from '@/lib/stores/insights'
import { usePomodoroPhaseSwitched } from '@/hooks/useTauriEvents'
import { PomodoroCountdown } from './PomodoroCountdown'
import { PomodoroProgress } from './PomodoroProgress'
import { PresetButtons } from './PresetButtons'
import { SessionInfoCard } from './SessionInfoCard'
import { TodoAssociationSelector } from './TodoAssociationSelector'
import { cn } from '@/lib/utils'

export function PomodoroTimer() {
  const { t } = useTranslation()
  const { status, session, error, config, setStatus, setSession, setError, reset, setConfig } = usePomodoroStore()
  const { todos } = useInsightsStore()

  const [userIntent, setUserIntent] = useState('')
  const [selectedTodoId, setSelectedTodoId] = useState<string | null>(null)

  // Listen for phase switches (work → break or break → work)
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

  // Auto-fill userIntent when todo is selected
  useEffect(() => {
    if (selectedTodoId) {
      const selectedTodo = todos.find((todo) => todo.id === selectedTodoId)
      if (selectedTodo) {
        setUserIntent(selectedTodo.title)
      }
    } else {
      // Clear userIntent when todo is deselected
      setUserIntent('')
    }
  }, [selectedTodoId, todos])

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

  const adjustValue = useCallback(
    (field: keyof typeof config, delta: number) => {
      const currentValue = config[field]
      let newValue = currentValue + delta

      // Set limits based on field
      if (field === 'totalRounds') {
        newValue = Math.max(1, Math.min(8, newValue))
      } else if (field === 'workDurationMinutes') {
        newValue = Math.max(5, Math.min(120, newValue))
      } else if (field === 'breakDurationMinutes') {
        newValue = Math.max(1, Math.min(60, newValue))
      }

      setConfig({ ...config, [field]: newValue })
    },
    [config, setConfig]
  )

  return (
    <Card className="w-full shadow-xl">
      <CardContent className="space-y-8">
        {status === 'idle' && (
          <div className="space-y-8">
            {/* TODO Association + Manual Input */}
            <Card
              className={cn(
                'py-0 transition-all duration-300',
                selectedTodoId
                  ? 'border-primary/30 bg-primary/5 ring-primary/10 shadow-md ring-2'
                  : 'border-border bg-muted/20'
              )}>
              <CardContent className="space-y-4 py-4">
                {/* TODO Association */}
                <TodoAssociationSelector selectedTodoId={selectedTodoId} onTodoSelect={setSelectedTodoId} />

                {/* Main Input - Only show when no todo is selected */}
                {!selectedTodoId && (
                  <div className="space-y-2">
                    <Label htmlFor="user-intent" className="text-base font-semibold">
                      {t('pomodoro.intent.label')}
                    </Label>
                    <Input
                      id="user-intent"
                      placeholder={t('pomodoro.intent.placeholder')}
                      value={userIntent}
                      onChange={(e) => setUserIntent(e.target.value)}
                      maxLength={200}
                      className="text-base"
                    />
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Configuration Section - Left: Custom Controls, Right: Presets */}
            <div className="flex flex-col gap-4 md:flex-row md:gap-6">
              {/* Left: Quick Setup Presets */}
              <div className="flex flex-1 flex-col gap-4 pt-2">
                <h3 className="flex items-center gap-2 text-lg font-semibold">
                  <Settings className="h-5 w-5" />
                  {t('pomodoro.presets.quickSetup')}
                </h3>
                <PresetButtons layout="vertical" />
              </div>
              {/* Right: Circular Config Controls */}
              <Card className="bg-muted/30 flex-2 border-2 py-0">
                <CardHeader className="pt-4">
                  <h3 className="flex items-center gap-2 text-lg font-semibold">
                    <Clock className="h-5 w-5" />
                    {t('pomodoro.config.custom')}
                  </h3>
                </CardHeader>
                <CardContent className="pb-6">
                  <div className="flex items-center justify-center gap-8">
                    {/* Total Rounds */}
                    <div className="flex flex-col items-center gap-3">
                      <div className="relative flex flex-col items-center">
                        {/* Up Arrow */}
                        <Button
                          variant="ghost"
                          size="icon"
                          className="hover:bg-muted/50 h-10 w-10 transition-all duration-200 hover:scale-110 active:scale-95"
                          onClick={() => adjustValue('totalRounds', 1)}>
                          <ChevronUp className="h-6 w-6" />
                        </Button>
                        {/* Circle with number */}
                        <div
                          className={cn(
                            'group relative flex h-32 w-32 items-center justify-center rounded-full border-4 shadow-lg',
                            'transition-all duration-300 ease-out',
                            'border-border hover:border-muted-foreground',
                            'from-card to-muted/50 bg-liner-to-br',
                            'hover:ring-muted/20 hover:scale-105 hover:shadow-2xl hover:ring-4'
                          )}>
                          <span className="text-6xl font-bold tabular-nums">{config.totalRounds}</span>
                        </div>
                        {/* Down Arrow */}
                        <Button
                          variant="ghost"
                          size="icon"
                          className="hover:bg-muted/50 h-10 w-10 transition-all duration-200 hover:scale-110 active:scale-95"
                          onClick={() => adjustValue('totalRounds', -1)}>
                          <ChevronDown className="h-6 w-6" />
                        </Button>
                      </div>
                      <span className="text-foreground text-sm font-semibold">{t('pomodoro.config.totalRounds')}</span>
                    </div>

                    {/* Work Duration */}
                    <div className="flex flex-col items-center gap-3">
                      <div className="relative flex flex-col items-center">
                        {/* Up Arrow */}
                        <Button
                          variant="ghost"
                          size="icon"
                          className="hover:bg-muted/50 h-10 w-10 transition-all duration-200 hover:scale-110 active:scale-95"
                          onClick={() => adjustValue('workDurationMinutes', 5)}>
                          <ChevronUp className="h-6 w-6" />
                        </Button>
                        {/* Circle with number */}
                        <div
                          className={cn(
                            'group relative flex h-32 w-32 items-center justify-center rounded-full border-4 shadow-lg',
                            'transition-all duration-300 ease-out',
                            'border-primary/40 hover:border-primary',
                            'from-card to-primary/5 bg-liner-to-br',
                            'hover:ring-primary/10 hover:scale-105 hover:shadow-2xl hover:ring-4'
                          )}>
                          <span className="text-6xl font-bold tabular-nums">{config.workDurationMinutes}</span>
                          {/* Optional watermark icon */}
                          <div className="absolute inset-0 flex items-center justify-center opacity-5">
                            <Clock className="h-16 w-16" />
                          </div>
                        </div>
                        {/* Down Arrow */}
                        <Button
                          variant="ghost"
                          size="icon"
                          className="hover:bg-muted/50 h-10 w-10 transition-all duration-200 hover:scale-110 active:scale-95"
                          onClick={() => adjustValue('workDurationMinutes', -5)}>
                          <ChevronDown className="h-6 w-6" />
                        </Button>
                      </div>
                      <div className="flex items-center gap-2">
                        <Clock className="text-primary h-4 w-4" />
                        <span className="text-foreground text-sm font-semibold">
                          {t('pomodoro.config.workDuration')}
                        </span>
                      </div>
                    </div>

                    {/* Break Duration */}
                    <div className="flex flex-col items-center gap-3">
                      <div className="relative flex flex-col items-center">
                        {/* Up Arrow */}
                        <Button
                          variant="ghost"
                          size="icon"
                          className="hover:bg-muted/50 h-10 w-10 transition-all duration-200 hover:scale-110 active:scale-95"
                          onClick={() => adjustValue('breakDurationMinutes', 1)}>
                          <ChevronUp className="h-6 w-6" />
                        </Button>
                        {/* Circle with number */}
                        <div
                          className={cn(
                            'group relative flex h-32 w-32 items-center justify-center rounded-full border-4 shadow-lg',
                            'transition-all duration-300 ease-out',
                            'border-chart-2/40 hover:border-chart-2',
                            'from-card to-chart-2/5 bg-linear-to-br',
                            'hover:ring-chart-2/10 hover:scale-105 hover:shadow-2xl hover:ring-4'
                          )}>
                          <span className="text-6xl font-bold tabular-nums">{config.breakDurationMinutes}</span>
                          {/* Optional watermark icon */}
                          <div className="absolute inset-0 flex items-center justify-center opacity-5">
                            <Coffee className="h-16 w-16" />
                          </div>
                        </div>
                        {/* Down Arrow */}
                        <Button
                          variant="ghost"
                          size="icon"
                          className="hover:bg-muted/50 h-10 w-10 transition-all duration-200 hover:scale-110 active:scale-95"
                          onClick={() => adjustValue('breakDurationMinutes', -1)}>
                          <ChevronDown className="h-6 w-6" />
                        </Button>
                      </div>
                      <div className="flex items-center gap-2">
                        <Coffee className="text-chart-2 h-4 w-4" />
                        <span className="text-foreground text-sm font-semibold">
                          {t('pomodoro.config.breakDuration')}
                        </span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Start Button */}
            <Button onClick={handleStart} className="w-full shadow-lg transition-all hover:shadow-xl" size="lg">
              <Play className="mr-2 h-5 w-5" />
              {t('pomodoro.start')}
            </Button>
          </div>
        )}

        {status === 'active' && session && (
          <div className="space-y-4">
            {/* Session Info Card */}
            <SessionInfoCard />

            {/* Countdown + Progress - Side by side */}
            <div className="flex flex-col items-center gap-4 md:flex-row md:items-center">
              {/* Countdown - Takes equal space */}
              <div className="flex flex-1 items-center justify-center pl-2">
                <PomodoroCountdown />
              </div>

              {/* Progress - Takes equal space */}
              <div className="flex flex-1 items-center justify-center">
                <PomodoroProgress />
              </div>
            </div>

            {/* End Button */}
            <Button onClick={handleEnd} variant="destructive" className="w-full" size="lg">
              <Square className="mr-2 h-5 w-5" />
              {t('pomodoro.end')}
            </Button>
          </div>
        )}

        {error && (
          <div className="bg-destructive/10 text-destructive rounded-md p-3 text-sm">
            <strong>{t('pomodoro.error.title')}:</strong> {error}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
