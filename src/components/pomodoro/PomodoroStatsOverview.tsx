import { Card, CardContent } from '@/components/ui/card'
import { Target, Clock, TrendingUp, Award } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useEffect, useState } from 'react'
import { getPomodoroGoals } from '@/lib/client/apiClient'

interface StatsOverviewProps {
  weeklyTotal: number
  focusHours: number
  dailyAverage: number
  completionRate: number
  period: 'week' | 'month' | 'year'
}

export function PomodoroStatsOverview({
  weeklyTotal,
  focusHours,
  dailyAverage,
  completionRate,
  period
}: StatsOverviewProps) {
  const { t } = useTranslation()
  const [weeklyGoalMinutes, setWeeklyGoalMinutes] = useState(600)

  useEffect(() => {
    const loadGoal = async () => {
      try {
        const response = await getPomodoroGoals()
        if (response.success && response.data) {
          setWeeklyGoalMinutes(response.data.weeklyFocusGoalMinutes)
        }
      } catch (error) {
        console.error('[PomodoroStatsOverview] Failed to load goal:', error)
      }
    }
    loadGoal()
  }, [])

  // Calculate goal hours based on period
  const getGoalHours = () => {
    if (period === 'week') {
      return weeklyGoalMinutes / 60
    } else if (period === 'month') {
      // Pro-rate weekly goal to monthly (4.3 weeks/month)
      return (weeklyGoalMinutes * 4.3) / 60
    } else if (period === 'year') {
      // Pro-rate weekly goal to yearly (52 weeks/year)
      return (weeklyGoalMinutes * 52) / 60
    }
    return weeklyGoalMinutes / 60
  }

  const goalHours = getGoalHours()

  const stats = [
    {
      icon: Target,
      value: weeklyTotal,
      label: t('pomodoro.review.overview.weeklyTotal'),
      unit: t('pomodoro.review.sessions')
    },
    {
      icon: Clock,
      value: focusHours.toFixed(1),
      label: t('pomodoro.review.overview.focusHours'),
      unit: 'h'
    },
    {
      icon: TrendingUp,
      value: dailyAverage,
      label: t('pomodoro.review.overview.dailyAverage'),
      unit: t('pomodoro.review.sessions')
    },
    {
      icon: Award,
      value: `${completionRate}%`,
      label: t('pomodoro.review.overview.completionRate'),
      unit: '',
      subtitle: `${focusHours}h / ${goalHours.toFixed(1)}h`
    }
  ]

  return (
    <div className="grid grid-cols-2 gap-4">
      {stats.map((stat, index) => {
        const Icon = stat.icon
        return (
          <Card key={index} className="shadow-none">
            <CardContent className="py-4">
              <div className="flex items-center justify-between gap-4">
                <div className="flex flex-col gap-0.5">
                  <span className="text-muted-foreground text-xs">{stat.label}</span>
                  <div className="flex items-baseline gap-1">
                    <span className="text-2xl font-bold tabular-nums">{stat.value}</span>
                    {stat.unit && <span className="text-muted-foreground text-sm">{stat.unit}</span>}
                  </div>
                  {'subtitle' in stat && stat.subtitle && (
                    <span className="text-muted-foreground text-xs">{stat.subtitle}</span>
                  )}
                </div>
                <div className="bg-primary/10 text-primary shrink-0 rounded-full p-2.5">
                  <Icon className="h-4 w-4" />
                </div>
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
