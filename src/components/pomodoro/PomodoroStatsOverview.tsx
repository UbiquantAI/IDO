import { Card, CardContent } from '@/components/ui/card'
import { Target, Clock, TrendingUp, Award } from 'lucide-react'
import { useTranslation } from 'react-i18next'

interface StatsOverviewProps {
  weeklyTotal: number
  focusHours: number
  dailyAverage: number
  completionRate: number
}

export function PomodoroStatsOverview({ weeklyTotal, focusHours, dailyAverage, completionRate }: StatsOverviewProps) {
  const { t } = useTranslation()

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
      unit: t('pomodoro.config.minutes')
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
      unit: ''
    }
  ]

  return (
    <div className="grid grid-cols-4 gap-4">
      {stats.map((stat, index) => {
        const Icon = stat.icon
        return (
          <Card key={index} className="shadow-none">
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="flex flex-col gap-1">
                  <span className="text-muted-foreground text-xs">{stat.label}</span>
                  <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-bold tabular-nums">{stat.value}</span>
                    {stat.unit && <span className="text-muted-foreground text-sm">{stat.unit}</span>}
                  </div>
                </div>
                <div className="bg-primary/10 text-primary rounded-full p-3">
                  <Icon className="h-5 w-5" />
                </div>
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
