import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { Target } from 'lucide-react'

import { PageLayout } from '@/components/layout/PageLayout'
import { PageHeader } from '@/components/layout/PageHeader'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent } from '@/components/ui/card'
import { DatePicker } from '@/components/ui/date-picker'
import { PomodoroTodoList } from '@/components/pomodoro/PomodoroTodoList'
import { PomodoroStatsOverview } from '@/components/pomodoro/PomodoroStatsOverview'
import { WeeklyFocusChart } from '@/components/pomodoro/WeeklyFocusChart'
import { TimePeriodSelector, TimePeriod } from '@/components/pomodoro/TimePeriodSelector'
import { SessionListItem } from '@/components/pomodoro/SessionListItem'
import { SessionDetailDialog } from '@/components/pomodoro/SessionDetailDialog'
import { usePomodoroEvents } from '@/hooks/usePomodoroEvents'
import { getPomodoroStats, getPomodoroPeriodStats } from '@/lib/client/apiClient'
import { Skeleton } from '@/components/ui/skeleton'

export default function Pomodoro() {
  const { t } = useTranslation()
  const [selectedPeriod, setSelectedPeriod] = useState<TimePeriod>('week')
  const [selectedDate, setSelectedDate] = useState<Date>(new Date())
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)

  // Fetch period statistics for overview
  const {
    data: periodStatsData,
    refetch: refetchPeriodStats,
    isLoading: isLoadingPeriodStats
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
      refetchStats()
      refetchPeriodStats()
    },
    onSessionDeleted: (payload) => {
      if (payload.id === selectedSessionId) {
        setSelectedSessionId(null)
        setDialogOpen(false)
      }
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
        title={t('pomodoro.title')}
        description={t('pomodoro.description')}
        actions={<TimePeriodSelector value={selectedPeriod} onChange={setSelectedPeriod} />}
      />

      <div className="flex min-h-0 flex-1 flex-col px-6 pb-6">
        <Tabs defaultValue="stats" className="flex min-h-0 flex-1 flex-col">
          <TabsList className="mb-4 w-fit">
            <TabsTrigger value="stats">{t('pomodoro.tabs.stats')}</TabsTrigger>
            <TabsTrigger value="history">{t('pomodoro.tabs.history')}</TabsTrigger>
          </TabsList>

          {/* Statistics + Todos Tab */}
          <TabsContent value="stats" className="min-h-0 flex-1">
            <div className="flex h-full gap-6">
              {/* Left: Todo List */}
              <aside className="hidden h-full w-[360px] shrink-0 md:block">
                <PomodoroTodoList selectedTodoId={null} onTodoSelect={() => {}} disabled={false} />
              </aside>

              {/* Right: Statistics */}
              <main className="min-h-0 min-w-0 flex-1 space-y-6 overflow-y-auto">
                {isLoadingPeriodStats ? (
                  <div className="space-y-4">
                    <div className="grid grid-cols-4 gap-4">
                      {[1, 2, 3, 4].map((i) => (
                        <Skeleton key={i} className="h-24" />
                      ))}
                    </div>
                    <Skeleton className="h-64" />
                  </div>
                ) : periodStats ? (
                  <>
                    <PomodoroStatsOverview
                      weeklyTotal={periodStats.weeklyTotal}
                      focusHours={periodStats.focusHours}
                      dailyAverage={periodStats.dailyAverage}
                      completionRate={periodStats.completionRate}
                      period={selectedPeriod}
                    />
                    {selectedPeriod === 'week' && <WeeklyFocusChart data={periodStats.dailyData} />}
                  </>
                ) : null}
              </main>
            </div>
          </TabsContent>

          {/* History Tab */}
          <TabsContent value="history" className="min-h-0 flex-1">
            <div className="flex h-full gap-6">
              {/* Left: Session List */}
              <div className="flex min-h-0 w-full shrink-0 flex-col space-y-4">
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
                          setSelectedSessionId(null)
                        }
                      }}
                      placeholder={t('pomodoro.review.selectDate')}
                    />
                  </div>
                </div>

                <div className="min-h-0 flex-1 space-y-3 overflow-y-auto">
                  <p className="text-muted-foreground text-sm">
                    {sessions.length}{' '}
                    {sessions.length === 1 ? t('pomodoro.review.session') : t('pomodoro.review.sessions')}{' '}
                    {t('pomodoro.review.on')} {format(selectedDate, 'MMM dd, yyyy')}
                  </p>

                  {sessions.length === 0 ? (
                    <Card className="shadow-none">
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
          </TabsContent>
        </Tabs>
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
