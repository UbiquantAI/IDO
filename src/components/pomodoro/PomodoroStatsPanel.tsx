import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { WeeklyFocusChart } from './WeeklyFocusChart'
import { TimePeriodSelector, TimePeriod } from './TimePeriodSelector'
import { usePomodoroEvents } from '@/hooks/usePomodoroEvents'
import { getPomodoroPeriodStats } from '@/lib/client/apiClient'
import { Skeleton } from '@/components/ui/skeleton'

export function PomodoroStatsPanel() {
  const { t } = useTranslation()
  const [selectedPeriod, setSelectedPeriod] = useState<TimePeriod>('week')

  // Fetch period statistics
  const {
    data: periodStatsData,
    refetch: refetchPeriodStats,
    isLoading
  } = useQuery({
    queryKey: ['pomodoro-period-stats', selectedPeriod],
    queryFn: async () => {
      const result = await getPomodoroPeriodStats({
        period: selectedPeriod,
        referenceDate: format(new Date(), 'yyyy-MM-dd')
      })
      return result
    }
  })

  // Listen to Pomodoro events to refresh stats
  usePomodoroEvents({
    onWorkPhaseCompleted: () => {
      refetchPeriodStats()
    },
    onSessionDeleted: () => {
      refetchPeriodStats()
    }
  })

  const periodStats = periodStatsData?.data

  return (
    <Card className="border-border/40 ring-border/5 flex h-full flex-col py-6 shadow-none ring-1 backdrop-blur-sm">
      {/* Header with period selector */}
      <CardHeader className="flex shrink-0 flex-row items-center justify-between space-y-0 pt-0 pb-4">
        <div>
          <CardTitle className="text-base">{t('pomodoro.review.statisticsPanel')}</CardTitle>
          <p className="text-muted-foreground mt-1 text-sm">{t('pomodoro.review.trackYourProgress')}</p>
        </div>
        <TimePeriodSelector value={selectedPeriod} onChange={setSelectedPeriod} />
      </CardHeader>

      {/* Stats content - scrollable */}
      <CardContent className="min-h-0 flex-1 space-y-4 overflow-y-auto">
        {isLoading ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-24" />
              ))}
            </div>
            <Skeleton className="h-64" />
          </div>
        ) : periodStats ? (
          <>
            {/* Statistics Overview Cards */}
            <div className="grid grid-cols-2 gap-4">
              {[
                {
                  label: t('pomodoro.review.overview.weeklyTotal'),
                  value: periodStats.weeklyTotal,
                  unit: t('pomodoro.review.sessions')
                },
                {
                  label: t('pomodoro.review.overview.focusHours'),
                  value: periodStats.focusHours.toFixed(1),
                  unit: 'h'
                },
                {
                  label: t('pomodoro.review.overview.dailyAverage'),
                  value: periodStats.dailyAverage,
                  unit: t('pomodoro.review.sessions')
                },
                {
                  label: t('pomodoro.review.overview.completionRate'),
                  value: `${periodStats.completionRate}%`,
                  unit: ''
                }
              ].map((stat, index) => (
                <Card key={index} className="shadow-none">
                  <CardContent className="px-5">
                    <div className="flex flex-col gap-1">
                      <span className="text-muted-foreground text-xs">{stat.label}</span>
                      <div className="flex items-baseline gap-1">
                        <span className="text-3xl font-bold tabular-nums">{stat.value}</span>
                        {stat.unit && <span className="text-muted-foreground text-sm">{stat.unit}</span>}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Weekly Focus Chart - Only show for week period */}
            {selectedPeriod === 'week' && <WeeklyFocusChart data={periodStats.dailyData} />}
          </>
        ) : (
          <Card className="shadow-none">
            <CardContent className="py-12 text-center">
              <p className="text-muted-foreground">{t('common.loading')}</p>
            </CardContent>
          </Card>
        )}
      </CardContent>
    </Card>
  )
}
