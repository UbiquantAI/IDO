import { useState, useEffect, useCallback } from 'react'
import { Clock, Play, Square, Loader2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import { toast } from 'sonner'
import { startPomodoro, endPomodoro, getPomodoroStatus } from '@/lib/client/apiClient'
import { usePomodoroStore } from '@/lib/stores/pomodoro'
import {
  usePomodoroProcessingProgress,
  usePomodoroProcessingComplete,
  usePomodoroProcessingFailed
} from '@/hooks/useTauriEvents'

export function PomodoroTimer() {
  const { t } = useTranslation()
  const { status, session, error, setStatus, setSession, setError, setProcessingJobId, reset } = usePomodoroStore()

  const [userIntent, setUserIntent] = useState('')
  const [durationMinutes, setDurationMinutes] = useState(25)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [processingProgress, setProcessingProgress] = useState(0)

  // Timer effect - counts elapsed time when session is active
  useEffect(() => {
    if (status === 'active' && session) {
      const timer = setInterval(() => {
        const now = Date.now()
        const start = new Date(session.startTime).getTime()
        const elapsed = Math.floor((now - start) / 1000)
        setElapsedSeconds(elapsed)
      }, 1000)

      return () => clearInterval(timer)
    }
  }, [status, session])

  // Event listeners for batch processing
  usePomodoroProcessingProgress((payload) => {
    console.log('[Pomodoro] Processing progress:', payload)
    if (payload.job_id === usePomodoroStore.getState().processingJobId) {
      setProcessingProgress(payload.processed)
    }
  })

  usePomodoroProcessingComplete((payload) => {
    console.log('[Pomodoro] Processing complete:', payload)
    if (payload.job_id === usePomodoroStore.getState().processingJobId) {
      toast.success(t('pomodoro.processing.complete', { count: payload.total_processed }))
      reset()
      setProcessingProgress(0)
    }
  })

  usePomodoroProcessingFailed((payload) => {
    console.log('[Pomodoro] Processing failed:', payload)
    if (payload.job_id === usePomodoroStore.getState().processingJobId) {
      toast.error(t('pomodoro.processing.failed', { error: payload.error }))
      setError(payload.error)
      setStatus('idle')
      setProcessingProgress(0)
    }
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

  const handleStart = useCallback(async () => {
    if (!userIntent.trim()) {
      toast.error(t('pomodoro.error.noIntent'))
      return
    }

    setStatus('active')
    setError(null)

    try {
      const result = await startPomodoro({
        userIntent: userIntent.trim(),
        durationMinutes
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
  }, [userIntent, durationMinutes, setStatus, setSession, setError, t])

  const handleEnd = useCallback(async () => {
    if (!session) return

    setStatus('ending')
    setError(null)

    try {
      const result = await endPomodoro({
        status: 'completed'
      })

      if (result.success && result.data) {
        const { processingJobId, rawRecordsCount, message } = result.data

        if (message) {
          toast.info(message)
          reset()
        } else {
          toast.success(t('pomodoro.ended', { count: rawRecordsCount }))
          setStatus('processing')
          setProcessingJobId(processingJobId || null)
        }
      } else {
        throw new Error(result.error || 'Failed to end Pomodoro')
      }
    } catch (err: any) {
      console.error('[Pomodoro] Failed to end:', err)
      setError(err.message || String(err))
      toast.error(t('pomodoro.error.endFailed', { error: err.message || String(err) }))
      setStatus('active') // Revert to active
    }
  }, [session, setStatus, setError, setProcessingJobId, reset, t])

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const progressPercent = session ? (elapsedSeconds / (session.plannedDurationMinutes * 60)) * 100 : 0

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock className="h-5 w-5" />
          {t('pomodoro.title')}
        </CardTitle>
        <CardDescription>{t('pomodoro.description')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {status === 'idle' && (
          <>
            <div className="space-y-2">
              <Label htmlFor="user-intent">{t('pomodoro.intent.label')}</Label>
              <Input
                id="user-intent"
                placeholder={t('pomodoro.intent.placeholder')}
                value={userIntent}
                onChange={(e) => setUserIntent(e.target.value)}
                maxLength={200}
              />
              <p className="text-muted-foreground text-sm">{t('pomodoro.intent.hint')}</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="duration">{t('pomodoro.duration.label')}</Label>
              <Input
                id="duration"
                type="number"
                min={1}
                max={90}
                value={durationMinutes}
                onChange={(e) => setDurationMinutes(Math.max(1, Math.min(90, parseInt(e.target.value) || 25)))}
              />
              <p className="text-muted-foreground text-sm">{t('pomodoro.duration.hint')}</p>
            </div>

            <Button onClick={handleStart} className="w-full" size="lg">
              <Play className="mr-2 h-4 w-4" />
              {t('pomodoro.start')}
            </Button>
          </>
        )}

        {status === 'active' && session && (
          <>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground text-sm">{t('pomodoro.status.active')}</span>
                <span className="font-mono text-2xl font-bold">{formatTime(elapsedSeconds)}</span>
              </div>
              <Progress value={Math.min(progressPercent, 100)} className="h-2" />
              <p className="text-muted-foreground text-sm">
                {t('pomodoro.intent.current')}: {session.userIntent}
              </p>
            </div>

            <Button onClick={handleEnd} variant="destructive" className="w-full" size="lg">
              <Square className="mr-2 h-4 w-4" />
              {t('pomodoro.end')}
            </Button>
          </>
        )}

        {(status === 'ending' || status === 'processing') && (
          <div className="space-y-2 text-center">
            <Loader2 className="mx-auto h-8 w-8 animate-spin" />
            <p className="text-muted-foreground text-sm">
              {status === 'ending' ? t('pomodoro.status.ending') : t('pomodoro.status.processing')}
            </p>
            {status === 'processing' && processingProgress > 0 && (
              <p className="text-muted-foreground text-xs">
                {t('pomodoro.processing.progress', { count: processingProgress })}
              </p>
            )}
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
