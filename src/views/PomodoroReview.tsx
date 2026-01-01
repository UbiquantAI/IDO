import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'

import { PageLayout } from '@/components/layout/PageLayout'
import { PageHeader } from '@/components/layout/PageHeader'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent } from '@/components/ui/card'
import { SessionListItem } from '@/components/pomodoro/SessionListItem'
import { SessionDetailDialog } from '@/components/pomodoro/SessionDetailDialog'
import { PomodoroStatsOverview } from '@/components/pomodoro/PomodoroStatsOverview'
import { WeeklyFocusChart } from '@/components/pomodoro/WeeklyFocusChart'
import { TimePeriodSelector, TimePeriod } from '@/components/pomodoro/TimePeriodSelector'
import { usePomodoroEvents } from '@/hooks/usePomodoroEvents'
import { getPomodoroStats, getPomodoroPeriodStats } from '@/lib/client/apiClient'
import { Target } from 'lucide-react'

export default function PomodoroReview() {
  const { t } = useTranslation()
  const [selectedDate, setSelectedDate] = useState<Date>(new Date())
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [selectedPeriod, setSelectedPeriod] = useState<TimePeriod>('week')

  // Fetch period statistics for overview
  const { data: periodStatsData, refetch: refetchPeriodStats } = useQuery({
    queryKey: ['pomodoro-period-stats', selectedPeriod],
    queryFn: async () => {
      const result = await getPomodoroPeriodStats({
        period: selectedPeriod,
        referenceDate: format(new Date(), 'yyyy-MM-dd')
      })
      return result
    }
  })

  // Fetch sessions for selected date
  const { data: statsData, refetch: refetchStats } = useQuery({
    queryKey: ['pomodoro-stats', format(selectedDate, 'yyyy-MM-dd')],
    queryFn: async () => {
      const result = await getPomodoroStats({ date: format(selectedDate, 'yyyy-MM-dd') })
      return result
    }
  })

  // Listen to Pomodoro events
  usePomodoroEvents({
    onWorkPhaseCompleted: () => {
      // Refresh stats list and period stats
      refetchStats()
      refetchPeriodStats()
    },
    onSessionDeleted: (payload) => {
      console.log('Session deleted:', payload.id)
      // Clear selection if deleted session was selected
      if (payload.id === selectedSessionId) {
        setSelectedSessionId(null)
        setDialogOpen(false)
      }
      // Refresh stats list and period stats
      refetchStats()
      refetchPeriodStats()
    }
  })

  const sessions = statsData?.data?.sessions || []
  const periodStats = periodStatsData?.data

  const handleSessionClick = (sessionId: string) => {
    setSelectedSessionId(sessionId)
    setDialogOpen(true)
  }

  const handleDialogClose = () => {
    setDialogOpen(false)
    // Don't clear selectedSessionId to preserve selection state
  }

  const handleSessionDeleted = () => {
    setSelectedSessionId(null)
    setDialogOpen(false)
    refetchStats()
    refetchPeriodStats()
  }

  return (
    <PageLayout stickyHeader>
      <PageHeader
        title={t('pomodoro.review.title') || 'Pomodoro Review'}
        description={t('pomodoro.review.description') || 'Review your focus sessions and track your productivity'}
        actions={<TimePeriodSelector value={selectedPeriod} onChange={setSelectedPeriod} />}
      />

      <div className="space-y-6 px-6 pb-6">
        {/* Statistics Overview Cards */}
        {periodStats && (
          <PomodoroStatsOverview
            weeklyTotal={periodStats.weeklyTotal}
            focusHours={periodStats.focusHours}
            dailyAverage={periodStats.dailyAverage}
            completionRate={periodStats.completionRate}
          />
        )}

        {/* Weekly Focus Chart - Only show for week period */}
        {selectedPeriod === 'week' && periodStats && <WeeklyFocusChart data={periodStats.dailyData} />}

        {/* Recent Sessions Section */}
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0 flex-1">
              <h3 className="text-base font-semibold">{t('pomodoro.review.recentSessions.title')}</h3>
              <p className="text-muted-foreground text-sm">{t('pomodoro.review.recentSessions.subtitle')}</p>
            </div>
            <div className="shrink-0">
              <DatePicker
                date={selectedDate}
                onDateChange={(date) => {
                  if (date) {
                    setSelectedDate(date)
                    setSelectedSessionId(null) // Clear selection when date changes
                  }
                }}
                placeholder={t('pomodoro.review.selectDate')}
              />
            </div>
          </div>

          {/* Session List */}
          <div className="space-y-3">
            <p className="text-muted-foreground text-sm">
              {sessions.length} {sessions.length === 1 ? t('pomodoro.review.session') : t('pomodoro.review.sessions')}{' '}
              {t('pomodoro.review.on')} {format(selectedDate, 'MMM dd, yyyy')}
            </p>

            {sessions.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <Target className="text-muted-foreground mx-auto h-12 w-12" />
                  <p className="text-muted-foreground mt-4">{t('pomodoro.review.noSessionsFound')}</p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-2">
                {sessions.map((session: any) => (
                  <SessionListItem
                    key={session.id}
                    session={session}
                    activityCount={session.activity_count || 0}
                    isSelected={session.id === selectedSessionId}
                    onClick={() => handleSessionClick(session.id)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Session Detail Dialog */}
      <SessionDetailDialog
        sessionId={selectedSessionId}
        open={dialogOpen}
        onOpenChange={handleDialogClose}
        onDeleted={handleSessionDeleted}
      />
    </PageLayout>
  )
}
