import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { FocusScoreVisualization } from './FocusScoreVisualization'
import { ActionCard } from '@/components/activity/ActionCard'
import { Clock, Hash, RefreshCw, ChevronDown, ChevronRight, Loader2, Layers, Coffee } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useState } from 'react'
import { toast } from 'sonner'
import { retryWorkPhaseAggregation, getActionsByActivity } from '@/lib/client/apiClient'
import type { Action } from '@/lib/types/activity'

interface Activity {
  id: string
  title: string
  description: string
  startTime?: string
  start_time?: string
  endTime?: string
  end_time?: string
  sessionDurationMinutes?: number
  session_duration_minutes?: number
  workPhase?: number | null
  work_phase?: number | null
  focusScore?: number | null
  focus_score?: number | null
  topicTags?: string[]
  topic_tags?: string[]
}

interface PhaseInfo {
  phaseType: 'work' | 'break'
  phaseNumber: number
  startTime: string
  endTime: string
  durationMinutes: number
}

interface SessionActivityTimelineProps {
  sessionId: string
  activities: Activity[]
  totalRounds: number
  phaseTimeline?: PhaseInfo[]
  onRetrySuccess?: () => void
}

export function SessionActivityTimeline({
  sessionId,
  activities,
  totalRounds,
  phaseTimeline = [],
  onRetrySuccess
}: SessionActivityTimelineProps) {
  const { t } = useTranslation()
  const [retryingPhase, setRetryingPhase] = useState<number | null>(null)
  const [expandedActivityId, setExpandedActivityId] = useState<string | null>(null)
  const [actionsMap, setActionsMap] = useState<Record<string, Action[]>>({})
  const [loadingActions, setLoadingActions] = useState<string | null>(null)

  // Handle retry work phase aggregation
  const handleRetryWorkPhase = async (workPhase: number) => {
    setRetryingPhase(workPhase)
    try {
      const result = await retryWorkPhaseAggregation({
        sessionId,
        workPhase
      })

      if (result.success) {
        toast.success(t('pomodoro.review.retrySuccess', { phase: workPhase }))
        // Notify parent to refetch data after a delay (give backend time to process)
        setTimeout(() => {
          onRetrySuccess?.()
        }, 3000)
      } else {
        toast.error(t('pomodoro.review.retryError'))
      }
    } catch (error) {
      console.error('[SessionActivityTimeline] Failed to retry work phase:', error)
      toast.error(t('pomodoro.review.retryError'))
    } finally {
      setRetryingPhase(null)
    }
  }

  // Handle toggle activity actions
  const handleToggleActions = async (activityId: string) => {
    if (expandedActivityId === activityId) {
      // Collapse
      setExpandedActivityId(null)
      return
    }

    // Expand and fetch actions if not already loaded
    setExpandedActivityId(activityId)

    if (!actionsMap[activityId]) {
      setLoadingActions(activityId)
      try {
        // Call the generated getActionsByActivity function
        // Note: API expects eventId field name but we're passing activityId value
        const result = await getActionsByActivity({ eventId: activityId })

        if (result.success && result.actions) {
          // Convert ActionResponse to Action (timestamp string to number)
          const actions: Action[] = result.actions.map((actionResponse) => ({
            id: actionResponse.id,
            title: actionResponse.title,
            description: actionResponse.description,
            keywords: actionResponse.keywords,
            timestamp: new Date(actionResponse.timestamp).getTime(),
            screenshots: actionResponse.screenshots,
            createdAt: actionResponse.createdAt ? new Date(actionResponse.createdAt).getTime() : undefined
          }))

          setActionsMap((prev) => ({
            ...prev,
            [activityId]: actions
          }))
        }
      } catch (error) {
        console.error('[SessionActivityTimeline] Failed to load actions:', error)
        toast.error('Failed to load actions')
      } finally {
        setLoadingActions(null)
      }
    }
  }

  // Group activities by work phase
  const activityGroups = activities.reduce(
    (acc, activity) => {
      const phase = activity.workPhase ?? activity.work_phase ?? 0
      if (!acc[phase]) {
        acc[phase] = []
      }
      acc[phase].push(activity)
      return acc
    },
    {} as Record<number, Activity[]>
  )

  // Format timestamp to readable time (24-hour format)
  const formatTime = (timestamp?: string) => {
    if (!timestamp) return '—'
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
  }

  // Get phase info for a specific phase number
  const getPhaseInfo = (phaseNumber: number): PhaseInfo | null => {
    const phase = phaseTimeline.find((p) => p.phaseType === 'work' && p.phaseNumber === phaseNumber)
    return phase || null
  }

  // Get break info after a specific work phase
  const getBreakInfo = (afterPhaseNumber: number): PhaseInfo | null => {
    const breakPhase = phaseTimeline.find((p) => p.phaseType === 'break' && p.phaseNumber === afterPhaseNumber)
    return breakPhase || null
  }

  if (activities.length === 0) {
    return (
      <div className="flex items-center justify-center rounded-lg border border-dashed p-8 text-center">
        <p className="text-muted-foreground">{t('pomodoro.review.activityTimeline.noActivities')}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {Array.from({ length: totalRounds }, (_, i) => i + 1).map((phase) => {
        const phaseActivities = activityGroups[phase] || []
        const phaseInfo = getPhaseInfo(phase)

        return (
          <div key={phase} className="border-primary relative border-l-2 pl-6">
            {/* Phase header */}
            <div className="bg-primary text-primary-foreground absolute top-0 -left-3 flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold">
              {phase}
            </div>
            <div className="mb-4">
              <div className="flex items-baseline justify-between">
                <h4 className="font-semibold">
                  {t('pomodoro.review.activityTimeline.workPhase')} {phase}
                </h4>
                {phaseInfo && (
                  <div className="text-muted-foreground text-xs">
                    {formatTime(phaseInfo.startTime)} - {formatTime(phaseInfo.endTime)}{' '}
                    <span className="text-muted-foreground/70">({phaseInfo.durationMinutes} min)</span>
                  </div>
                )}
              </div>
              <p className="text-muted-foreground text-sm">
                {phaseActivities.length}{' '}
                {phaseActivities.length === 1
                  ? t('pomodoro.review.activityTimeline.activity')
                  : t('pomodoro.review.activityTimeline.activities')}
              </p>
            </div>

            {/* Activities for this phase */}
            <div className="space-y-3">
              {phaseActivities.length === 0 ? (
                <div className="space-y-3 rounded-lg border border-dashed p-4">
                  <p className="text-muted-foreground text-sm italic">
                    {t('pomodoro.review.activityTimeline.noActivitiesInPhase')}
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleRetryWorkPhase(phase)}
                    disabled={retryingPhase === phase}
                    className="w-full">
                    {retryingPhase === phase ? (
                      <>
                        <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                        {t('pomodoro.review.retrying')}
                      </>
                    ) : (
                      <>
                        <RefreshCw className="mr-2 h-4 w-4" />
                        {t('pomodoro.review.retryAggregation')}
                      </>
                    )}
                  </Button>
                </div>
              ) : (
                phaseActivities.map((activity) => (
                  <Card key={activity.id} className="shadow-sm">
                    <CardHeader>
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <CardTitle className="text-base">{activity.title}</CardTitle>
                          <p className="text-muted-foreground mt-1 text-sm">{activity.description}</p>
                        </div>
                        {activity.focusScore !== null && activity.focusScore !== undefined && (
                          <FocusScoreVisualization score={activity.focusScore} size="sm" showLabel={false} />
                        )}
                        {activity.focusScore === undefined &&
                          activity.focus_score !== null &&
                          activity.focus_score !== undefined && (
                            <FocusScoreVisualization score={activity.focus_score} size="sm" showLabel={false} />
                          )}
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="flex flex-wrap items-center gap-4 text-sm">
                        <div className="text-muted-foreground flex items-center gap-1.5">
                          <Clock className="h-4 w-4" />
                          <span>
                            {formatTime(activity.startTime ?? activity.start_time)} -{' '}
                            {formatTime(activity.endTime ?? activity.end_time)}
                          </span>
                          <span className="text-muted-foreground/70">
                            ({activity.sessionDurationMinutes ?? activity.session_duration_minutes ?? 0} min)
                          </span>
                        </div>
                        {(activity.topicTags ?? activity.topic_tags ?? []).length > 0 && (
                          <div className="flex items-center gap-1.5">
                            <Hash className="text-muted-foreground h-4 w-4" />
                            <div className="flex flex-wrap gap-1">
                              {(activity.topicTags ?? activity.topic_tags ?? []).map((tag) => (
                                <Badge key={tag} variant="secondary" className="text-xs">
                                  {tag}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Actions drill-down */}
                      <div className="mt-4 space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="text-muted-foreground flex items-center gap-2 text-xs font-semibold uppercase">
                            <Layers className="h-3.5 w-3.5" />
                            Actions
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleToggleActions(activity.id)}
                            className="h-7 text-xs">
                            {expandedActivityId === activity.id ? (
                              <>
                                <ChevronDown className="mr-1 h-3 w-3" />
                                Hide Actions
                              </>
                            ) : (
                              <>
                                <ChevronRight className="mr-1 h-3 w-3" />
                                View Actions
                              </>
                            )}
                            {loadingActions === activity.id && <Loader2 className="ml-2 h-3 w-3 animate-spin" />}
                          </Button>
                        </div>

                        {/* Actions list */}
                        {expandedActivityId === activity.id && (
                          <div className="space-y-2">
                            {loadingActions === activity.id ? (
                              <div className="border-border text-muted-foreground flex items-center justify-center gap-2 rounded-lg border border-dashed py-6 text-xs">
                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                Loading Actions...
                              </div>
                            ) : actionsMap[activity.id] && actionsMap[activity.id].length > 0 ? (
                              actionsMap[activity.id].map((action) => <ActionCard key={action.id} action={action} />)
                            ) : (
                              <div className="border-border text-muted-foreground rounded-lg border border-dashed py-6 text-center text-xs">
                                No actions found
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>

            {/* Break period after this work phase (if exists and not the last phase) */}
            {phase < totalRounds &&
              (() => {
                const breakInfo = getBreakInfo(phase)
                if (!breakInfo) return null

                return (
                  <div className="bg-muted/30 mt-4 flex items-center gap-3 rounded-lg border border-dashed p-3">
                    <Coffee className="text-muted-foreground h-4 w-4 flex-shrink-0" />
                    <div className="flex-1">
                      <div className="text-muted-foreground text-sm font-medium">
                        {t('pomodoro.review.activityTimeline.breakTime')}
                      </div>
                      <div className="text-muted-foreground/70 text-xs">
                        {formatTime(breakInfo.startTime)} - {formatTime(breakInfo.endTime)} ({breakInfo.durationMinutes}{' '}
                        min)
                      </div>
                    </div>
                  </div>
                )
              })()}
          </div>
        )
      })}
    </div>
  )
}
