import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { Loader2 } from 'lucide-react'
import { getPomodoroGoals, updatePomodoroGoals } from '@/lib/client/apiClient'

interface GoalsSetupStepProps {
  onContinue: () => void
}

export function GoalsSetupStep({ onContinue }: GoalsSetupStepProps) {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [dailyGoal, setDailyGoal] = useState(120) // 2 hours default
  const [weeklyGoal, setWeeklyGoal] = useState(600) // 10 hours default

  // Load current goals
  useEffect(() => {
    const loadGoals = async () => {
      try {
        const response = await getPomodoroGoals()
        if (response.success && response.data) {
          setDailyGoal(response.data.dailyFocusGoalMinutes)
          setWeeklyGoal(response.data.weeklyFocusGoalMinutes)
        }
      } catch (error) {
        console.error('[GoalsSetupStep] Failed to load goals:', error)
      } finally {
        setLoading(false)
      }
    }
    loadGoals()
  }, [])

  const handleContinue = async () => {
    setSaving(true)
    try {
      const response = await updatePomodoroGoals({
        dailyFocusGoalMinutes: dailyGoal,
        weeklyFocusGoalMinutes: weeklyGoal
      })

      if (response.success) {
        toast.success(t('setup.goals.saveSuccess'))
        onContinue()
      } else {
        toast.error(t('setup.goals.saveFailed'))
      }
    } catch (error) {
      console.error('[GoalsSetupStep] Failed to save goals:', error)
      toast.error(t('setup.goals.saveFailed'))
    } finally {
      setSaving(false)
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
    <div className="space-y-8">
      <div className="space-y-3">
        <h2 className="text-3xl font-bold">{t('setup.goals.heading')}</h2>
        <p className="text-muted-foreground text-base">{t('setup.goals.description')}</p>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed p-10 text-center">
          <Loader2 className="text-muted-foreground mb-3 h-8 w-8 animate-spin" />
          <p className="text-muted-foreground">{t('common.loading')}</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Daily Goal */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>{t('setup.goals.dailyGoalTitle')}</Label>
              <span className="text-muted-foreground text-sm">{formatHours(dailyGoal)}</span>
            </div>
            <Slider
              value={[dailyGoal]}
              onValueChange={(value) => setDailyGoal(value[0])}
              min={30}
              max={720}
              step={30}
              className="w-full"
            />
            <p className="text-muted-foreground text-xs">{t('setup.goals.dailyGoalDescription')}</p>
          </div>

          {/* Weekly Goal */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>{t('setup.goals.weeklyGoalTitle')}</Label>
              <span className="text-muted-foreground text-sm">{formatHours(weeklyGoal)}</span>
            </div>
            <Slider
              value={[weeklyGoal]}
              onValueChange={(value) => setWeeklyGoal(value[0])}
              min={60}
              max={2520}
              step={60}
              className="w-full"
            />
            <p className="text-muted-foreground text-xs">{t('setup.goals.weeklyGoalDescription')}</p>
          </div>
        </div>
      )}

      <div className="flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-muted-foreground text-sm">{t('setup.goals.continueHint')}</p>
        <Button onClick={handleContinue} disabled={loading || saving} className="gap-2">
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          {t('setup.actions.continue')}
        </Button>
      </div>
    </div>
  )
}
