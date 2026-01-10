import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { useEffect, useState } from 'react'
import { getPomodoroGoals, updatePomodoroGoals } from '@/lib/client/apiClient'

export function PomodoroSettings() {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)
  const [dailyGoal, setDailyGoal] = useState(120)
  const [weeklyGoal, setWeeklyGoal] = useState(600)
  const [localDailyGoal, setLocalDailyGoal] = useState<number | null>(null)
  const [localWeeklyGoal, setLocalWeeklyGoal] = useState<number | null>(null)

  // Load goals on mount
  useEffect(() => {
    const loadGoals = async () => {
      try {
        const response = await getPomodoroGoals()
        if (response.success && response.data) {
          setDailyGoal(response.data.dailyFocusGoalMinutes)
          setWeeklyGoal(response.data.weeklyFocusGoalMinutes)
        }
      } catch (error) {
        console.error('[PomodoroSettings] Failed to load goals:', error)
        toast.error(t('settings.pomodoro.loadFailed'))
      } finally {
        setLoading(false)
      }
    }
    loadGoals()
  }, [t])

  const handleDailyGoalChange = async (value: number[]) => {
    setLocalDailyGoal(null)
    setUpdating(true)
    try {
      const response = await updatePomodoroGoals({
        dailyFocusGoalMinutes: value[0]
      })
      if (response.success && response.data) {
        setDailyGoal(response.data.dailyFocusGoalMinutes)
        toast.success(t('settings.pomodoro.dailyGoalUpdated'))
      }
    } catch (error) {
      toast.error(t('settings.pomodoro.updateFailed'))
    } finally {
      setUpdating(false)
    }
  }

  const handleWeeklyGoalChange = async (value: number[]) => {
    setLocalWeeklyGoal(null)
    setUpdating(true)
    try {
      const response = await updatePomodoroGoals({
        weeklyFocusGoalMinutes: value[0]
      })
      if (response.success && response.data) {
        setWeeklyGoal(response.data.weeklyFocusGoalMinutes)
        toast.success(t('settings.pomodoro.weeklyGoalUpdated'))
      }
    } catch (error) {
      toast.error(t('settings.pomodoro.updateFailed'))
    } finally {
      setUpdating(false)
    }
  }

  const formatHours = (minutes: number) => {
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    if (mins === 0) {
      return `${hours}h`
    }
    return `${hours}h ${mins}m`
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('settings.pomodoro.title')}</CardTitle>
        <CardDescription>{t('settings.pomodoro.description')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Daily Goal */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label>{t('settings.pomodoro.dailyGoalTitle')}</Label>
            <span className="text-muted-foreground text-sm">{formatHours(localDailyGoal ?? dailyGoal)}</span>
          </div>
          <Slider
            value={[localDailyGoal ?? dailyGoal]}
            onValueChange={(value) => setLocalDailyGoal(value[0])}
            onValueCommit={handleDailyGoalChange}
            min={30}
            max={720}
            step={30}
            disabled={loading || updating}
            className="w-full"
          />
          <p className="text-muted-foreground text-xs">{t('settings.pomodoro.dailyGoalDescription')}</p>
        </div>

        {/* Weekly Goal */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label>{t('settings.pomodoro.weeklyGoalTitle')}</Label>
            <span className="text-muted-foreground text-sm">{formatHours(localWeeklyGoal ?? weeklyGoal)}</span>
          </div>
          <Slider
            value={[localWeeklyGoal ?? weeklyGoal]}
            onValueChange={(value) => setLocalWeeklyGoal(value[0])}
            onValueCommit={handleWeeklyGoalChange}
            min={60}
            max={2520}
            step={60}
            disabled={loading || updating}
            className="w-full"
          />
          <p className="text-muted-foreground text-xs">{t('settings.pomodoro.weeklyGoalDescription')}</p>
        </div>
      </CardContent>
    </Card>
  )
}
