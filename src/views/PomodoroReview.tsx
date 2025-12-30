import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'

import { PageLayout } from '@/components/layout/PageLayout'
import { PageHeader } from '@/components/layout/PageHeader'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { SessionReviewCard } from '@/components/pomodoro/SessionReviewCard'
import { SessionActivityTimeline } from '@/components/pomodoro/SessionActivityTimeline'
import { FocusScoreVisualization } from '@/components/pomodoro/FocusScoreVisualization'
import { LinkActivitiesDialog } from '@/components/pomodoro/LinkActivitiesDialog'
import { usePomodoroEvents } from '@/hooks/usePomodoroEvents'
import { getPomodoroStats, getPomodoroSessionDetail } from '@/lib/client/apiClient'
import { Activity, TrendingUp, Clock, Target } from 'lucide-react'

export default function PomodoroReview() {
  const { t } = useTranslation()
  const [selectedDate, setSelectedDate] = useState<Date>(new Date())
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)

  // Fetch sessions for selected date
  const { data: statsData, refetch: refetchStats } = useQuery({
    queryKey: ['pomodoro-stats', format(selectedDate, 'yyyy-MM-dd')],
    queryFn: async () => {
      const result = await getPomodoroStats({ date: format(selectedDate, 'yyyy-MM-dd') })
      return result
    }
  })

  // Fetch detailed data for selected session
  const { data: sessionDetail, refetch: refetchDetail } = useQuery({
    queryKey: ['pomodoro-session-detail', selectedSessionId],
    queryFn: async () => {
      if (!selectedSessionId) return null
      const result = await getPomodoroSessionDetail({ sessionId: selectedSessionId })
      return result
    },
    enabled: !!selectedSessionId
  })

  // Listen to Pomodoro events
  usePomodoroEvents({
    onWorkPhaseCompleted: (payload) => {
      console.log('Work phase completed:', payload)
      // Refresh session detail if it's the currently selected session
      if (payload.session_id === selectedSessionId) {
        refetchDetail()
      }
      // Refresh stats list
      refetchStats()
    },
    onSessionDeleted: (payload) => {
      console.log('Session deleted:', payload.id)
      // Clear selection if deleted session was selected
      if (payload.id === selectedSessionId) {
        setSelectedSessionId(null)
      }
      // Refresh stats list
      refetchStats()
    }
  })

  const sessions = statsData?.data?.sessions || []
  const detailData = sessionDetail?.data

  return (
    <PageLayout>
      <PageHeader
        title={t('pomodoro.review.title') || 'Pomodoro Review'}
        description={t('pomodoro.review.description') || 'Review your focus sessions and track your productivity'}
      />

      <div className="flex-1 overflow-hidden px-6 py-2">
        <div className="grid h-full grid-cols-12 gap-6">
          {/* Left sidebar: Date picker + session list */}
          <div className="col-span-4 flex flex-col gap-4 overflow-y-auto">
            <div className="flex flex-col gap-4">
              <DatePicker
                date={selectedDate}
                onDateChange={(date) => {
                  if (date) {
                    setSelectedDate(date)
                    setSelectedSessionId(null) // Clear selection when date changes
                  }
                }}
                placeholder={t('pomodoro.review.selectDate')}
                fullWidth={true}
              />

              <h3 className="text-sm font-semibold">
                {sessions.length} {sessions.length === 1 ? t('pomodoro.review.session') : t('pomodoro.review.sessions')}{' '}
                {t('pomodoro.review.on')} {format(selectedDate, 'MMM dd, yyyy')}
              </h3>
            </div>

            <div className="flex-1 space-y-4 overflow-y-auto">
              {sessions.length === 0 ? (
                <Card>
                  <CardContent className="py-8 text-center">
                    <p className="text-muted-foreground">{t('pomodoro.review.noSessionsFound')}</p>
                  </CardContent>
                </Card>
              ) : (
                sessions.map((session: any) => (
                  <SessionReviewCard
                    key={session.id}
                    session={session}
                    activityCount={session.activity_count || 0}
                    focusLevel="moderate" // Default, will be replaced with actual data
                    onViewDetails={() => setSelectedSessionId(session.id)}
                    onDeleted={() => {
                      // Clear selection if this was the selected session
                      if (session.id === selectedSessionId) {
                        setSelectedSessionId(null)
                      }
                      // Refetch stats to update the list
                      refetchStats()
                    }}
                  />
                ))
              )}
            </div>
          </div>

          {/* Right main area: Detailed session view */}
          <div className="col-span-8 overflow-y-auto">
            {!selectedSessionId || !detailData ? (
              <Card className="h-full">
                <CardContent className="flex h-full items-center justify-center py-12">
                  <div className="text-center">
                    <Target className="text-muted-foreground mx-auto h-12 w-12" />
                    <p className="text-muted-foreground mt-4">{t('pomodoro.review.selectSessionPrompt')}</p>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-6">
                {/* Session header */}
                <Card>
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <CardTitle>{(detailData.session as any).user_intent}</CardTitle>
                        <div className="text-muted-foreground mt-2 flex items-center gap-4 text-sm">
                          <div className="flex items-center gap-1.5">
                            <Clock className="h-4 w-4" />
                            <span>{(detailData.session as any).pure_work_duration_minutes || 0} minutes</span>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <Activity className="h-4 w-4" />
                            <span>
                              {(detailData.session as any).completed_rounds || 0} /{' '}
                              {(detailData.session as any).total_rounds || 0} rounds
                            </span>
                          </div>
                        </div>
                      </div>
                      <LinkActivitiesDialog sessionId={selectedSessionId!} onLinked={() => refetchDetail()} />
                    </div>
                  </CardHeader>
                </Card>

                {/* Focus metrics overview */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <TrendingUp className="h-5 w-5" />
                      {t('pomodoro.review.focusMetrics.title')}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 gap-6">
                      <div className="flex justify-center">
                        <FocusScoreVisualization
                          score={(detailData.focusMetrics as any)?.overallFocusScore || 0}
                          size="lg"
                          showLabel={true}
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="rounded-lg border p-4">
                          <p className="text-muted-foreground text-sm">
                            {t('pomodoro.review.focusMetrics.activities')}
                          </p>
                          <p className="mt-1 text-2xl font-bold">
                            {(detailData.focusMetrics as any)?.activityCount || 0}
                          </p>
                        </div>
                        <div className="rounded-lg border p-4">
                          <p className="text-muted-foreground text-sm">{t('pomodoro.review.focusMetrics.topics')}</p>
                          <p className="mt-1 text-2xl font-bold">
                            {(detailData.focusMetrics as any)?.topicDiversity || 0}
                          </p>
                        </div>
                        <div className="col-span-2 rounded-lg border p-4">
                          <p className="text-muted-foreground text-sm">
                            {t('pomodoro.review.focusMetrics.avgDuration')}
                          </p>
                          <p className="mt-1 text-2xl font-bold">
                            {(detailData.focusMetrics as any)?.averageActivityDuration || 0}{' '}
                            {t('pomodoro.review.focusMetrics.minutes')}
                          </p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Activity timeline with integrated phase timeline */}
                <Card>
                  <CardHeader>
                    <CardTitle>{t('pomodoro.review.activityTimeline.title')}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <SessionActivityTimeline
                      sessionId={selectedSessionId}
                      activities={detailData.activities as any}
                      totalRounds={(detailData.session as any).total_rounds || 4}
                      phaseTimeline={detailData.phaseTimeline as any}
                      onRetrySuccess={() => refetchDetail()}
                    />
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        </div>
      </div>
    </PageLayout>
  )
}
