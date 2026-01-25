import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useTranslation } from 'react-i18next'
import { useEffect, useState } from 'react'
import { cn } from '@/lib/utils'
import { getPomodoroGoals } from '@/lib/client/apiClient'

interface DailyFocusData {
  day: string
  sessions: number
  minutes: number
}

interface WeeklyFocusChartProps {
  data: DailyFocusData[]
}

export function WeeklyFocusChart({ data }: WeeklyFocusChartProps) {
  const { t } = useTranslation()
  const [dailyGoalMinutes, setDailyGoalMinutes] = useState(120)

  // Load daily goal for scaling
  useEffect(() => {
    const loadGoal = async () => {
      try {
        const response = await getPomodoroGoals()
        if (response.success && response.data) {
          setDailyGoalMinutes(response.data.dailyFocusGoalMinutes)
        }
      } catch (error) {
        console.error('[WeeklyFocusChart] Failed to load goal:', error)
      }
    }
    loadGoal()
  }, [])

  // Use daily goal as the 100% reference for progress bars
  const maxMinutes = dailyGoalMinutes

  return (
    <Card className="card-hover animate-in fade-in slide-in-from-bottom-2 shadow-none duration-300">
      <CardHeader>
        <CardTitle className="text-base">{t('pomodoro.review.weeklyFocus.title')}</CardTitle>
        <p className="text-muted-foreground text-sm">{t('pomodoro.review.weeklyFocus.subtitle')}</p>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {data.map((item, index) => {
            const percentage = (item.minutes / maxMinutes) * 100
            const isOverGoal = percentage > 100

            return (
              <div
                key={item.day}
                className="animate-in fade-in slide-in-from-left-2 flex items-center gap-3 duration-200"
                style={{ animationDelay: `${index * 40}ms`, animationFillMode: 'backwards' }}>
                <div className="text-muted-foreground w-12 text-sm">{item.day}</div>
                <div className="flex-1">
                  <div className="bg-muted h-8 overflow-hidden rounded-full">
                    <div
                      className={cn(
                        'flex h-full items-center justify-end pr-3 transition-all duration-500',
                        item.sessions === 0 && 'bg-muted',
                        item.sessions > 0 && !isOverGoal && 'bg-primary',
                        isOverGoal && 'bg-green-600'
                      )}
                      style={{ width: `${Math.min(percentage, 100)}%` }}>
                      {item.sessions > 0 && (
                        <span className="text-primary-foreground text-xs font-medium">
                          {item.minutes} {t('pomodoro.review.weeklyFocus.minutes')}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="text-muted-foreground w-12 text-right text-xs">{Math.round(percentage)}%</div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
