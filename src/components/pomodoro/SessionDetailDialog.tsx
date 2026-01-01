import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import {
  Clock,
  Activity,
  TrendingUp,
  Trash2,
  Loader2,
  Sparkles,
  ChevronDown,
  ThumbsUp,
  AlertCircle,
  Lightbulb
} from 'lucide-react'
import { useState, useCallback } from 'react'
import { toast } from 'sonner'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { FocusScoreVisualization } from './FocusScoreVisualization'
import { SessionActivityTimeline } from './SessionActivityTimeline'
import { LinkActivitiesDialog } from './LinkActivitiesDialog'
import { getPomodoroSessionDetail, deletePomodoroSession } from '@/lib/client/apiClient'

interface SessionDetailDialogProps {
  sessionId: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onDeleted?: () => void
}

export function SessionDetailDialog({ sessionId, open, onOpenChange, onDeleted }: SessionDetailDialogProps) {
  const { t } = useTranslation()
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)

  // Fetch detailed data for selected session
  const { data: sessionDetail, refetch: refetchDetail } = useQuery({
    queryKey: ['pomodoro-session-detail', sessionId],
    queryFn: async () => {
      if (!sessionId) return null
      const result = await getPomodoroSessionDetail({ sessionId })
      return result
    },
    enabled: !!sessionId && open
  })

  const detailData = sessionDetail?.data

  const handleDelete = useCallback(async () => {
    if (!sessionId || isDeleting) return

    setIsDeleting(true)
    try {
      const result = await deletePomodoroSession({ sessionId })
      if (result.success) {
        toast.success(t('pomodoro.review.deleteSuccess'))
        setDeleteDialogOpen(false)
        onOpenChange(false)
        onDeleted?.()
      } else {
        toast.error(t('pomodoro.review.deleteError'))
      }
    } catch (error) {
      console.error('[SessionDetailDialog] Failed to delete session:', error)
      toast.error(t('pomodoro.review.deleteError'))
    } finally {
      setIsDeleting(false)
    }
  }, [sessionId, isDeleting, onDeleted, onOpenChange, t])

  // Skeleton loading component
  const LoadingSkeleton = () => (
    <>
      <DialogHeader>
        <DialogTitle>{t('pomodoro.review.sessionDetails', 'Session Details')}</DialogTitle>
        <DialogDescription>{t('pomodoro.review.loadingSession', 'Loading session data...')}</DialogDescription>
      </DialogHeader>

      <div className="space-y-6 py-4">
        {/* Focus metrics skeleton */}
        <Card>
          <CardHeader>
            <Skeleton className="h-5 w-32" />
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-6">
              <div className="flex justify-center">
                <Skeleton className="h-32 w-32 rounded-full" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <Skeleton className="h-24 rounded-lg" />
                <Skeleton className="h-24 rounded-lg" />
                <Skeleton className="col-span-2 h-24 rounded-lg" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Activity timeline skeleton */}
        <Card>
          <CardHeader>
            <Skeleton className="h-5 w-40" />
          </CardHeader>
          <CardContent className="space-y-4">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </CardContent>
        </Card>
      </div>
    </>
  )

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-4xl">
          {!detailData ? (
            <LoadingSkeleton />
          ) : (
            <>
              <DialogHeader>
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <DialogTitle className="text-xl">{(detailData.session as any).user_intent}</DialogTitle>
                    <div className="text-muted-foreground mt-2 flex items-center gap-4 text-sm">
                      <div className="flex items-center gap-1.5">
                        <Clock className="h-4 w-4" />
                        <span>
                          {(detailData.session as any).pure_work_duration_minutes || 0}{' '}
                          {t('pomodoro.review.focusMetrics.minutes')}
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Activity className="h-4 w-4" />
                        <span>
                          {(detailData.session as any).completed_rounds || 0}{' '}
                          {(detailData.session as any).completed_rounds === 1
                            ? t('pomodoro.review.round')
                            : t('pomodoro.review.rounds')}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <LinkActivitiesDialog sessionId={sessionId!} onLinked={() => refetchDetail()} />
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setDeleteDialogOpen(true)}
                      className="text-destructive hover:text-destructive"
                      title={t('pomodoro.review.deleteSession')}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </DialogHeader>

              <div className="space-y-6 py-4">
                {/* Focus metrics overview */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <TrendingUp className="h-4 w-4" />
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
                    <CardTitle className="text-base">{t('pomodoro.review.activityTimeline.title')}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <SessionActivityTimeline
                      sessionId={sessionId!}
                      activities={detailData.activities as any}
                      totalRounds={(detailData.session as any).total_rounds || 4}
                      phaseTimeline={detailData.phaseTimeline as any}
                      onRetrySuccess={() => refetchDetail()}
                    />
                  </CardContent>
                </Card>

                {/* AI Analysis Panel */}
                {detailData.llmFocusEvaluation && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-base">
                        <Sparkles className="h-4 w-4" />
                        {t('pomodoro.review.aiAnalysis.title')}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <Collapsible defaultOpen={false}>
                        <CollapsibleTrigger asChild>
                          <Button variant="ghost" size="sm" className="w-full justify-between">
                            <span className="flex items-center gap-2">
                              <span>{t('pomodoro.review.aiAnalysis.viewDetails')}</span>
                              <Badge variant="outline">
                                {t(
                                  `pomodoro.review.focusLevel.${(detailData.llmFocusEvaluation as any).focusLevel}` as any
                                )}
                              </Badge>
                            </span>
                            <ChevronDown className="h-4 w-4 transition-transform" />
                          </Button>
                        </CollapsibleTrigger>

                        <CollapsibleContent className="space-y-6 pt-4">
                          {/* Dimension scores */}
                          <div>
                            <h4 className="mb-4 text-sm font-medium">
                              {t('pomodoro.review.aiAnalysis.dimensionScores')}
                            </h4>
                            <div className="space-y-3">
                              {Object.entries((detailData.llmFocusEvaluation as any).dimensionScores).map(
                                ([key, value]: [string, any]) => (
                                  <div key={key} className="space-y-1">
                                    <div className="flex justify-between text-sm">
                                      <span className="text-muted-foreground">
                                        {t(`pomodoro.review.aiAnalysis.dimensions.${key}` as any)}
                                      </span>
                                      <span className="font-medium">{value}/100</span>
                                    </div>
                                    <Progress value={value} className="h-2" />
                                  </div>
                                )
                              )}
                            </div>
                          </div>

                          {/* Work context */}
                          <div>
                            <h4 className="mb-2 text-sm font-medium">{t('pomodoro.review.aiAnalysis.workContext')}</h4>
                            <p className="text-muted-foreground text-sm">
                              {(detailData.llmFocusEvaluation as any).contextSummary}
                            </p>
                            <div className="mt-2 flex flex-wrap gap-2">
                              <Badge variant="outline">
                                {t(
                                  `pomodoro.review.aiAnalysis.workTypes.${(detailData.llmFocusEvaluation as any).workType}` as any
                                )}
                              </Badge>
                              {(detailData.llmFocusEvaluation as any).isFocusedWork && (
                                <Badge variant="default">{t('pomodoro.review.aiAnalysis.focusedWork')}</Badge>
                              )}
                              <Badge variant="secondary">
                                {(detailData.llmFocusEvaluation as any).deepWorkMinutes}{' '}
                                {t('pomodoro.review.aiAnalysis.deepWork')}
                              </Badge>
                            </div>
                          </div>

                          {/* Strengths */}
                          <div>
                            <h4 className="mb-2 flex items-center gap-2 text-sm font-medium text-green-600">
                              <ThumbsUp className="h-4 w-4" />
                              {t('pomodoro.review.aiAnalysis.strengths')}
                            </h4>
                            <ul className="space-y-1">
                              {(detailData.llmFocusEvaluation as any).analysis.strengths.map(
                                (strength: string, idx: number) => (
                                  <li key={idx} className="text-muted-foreground flex items-start gap-2 text-sm">
                                    <span className="mt-1 text-green-600">✓</span>
                                    <span>{strength}</span>
                                  </li>
                                )
                              )}
                            </ul>
                          </div>

                          {/* Weaknesses */}
                          {(detailData.llmFocusEvaluation as any).analysis.weaknesses.length > 0 && (
                            <div>
                              <h4 className="mb-2 flex items-center gap-2 text-sm font-medium text-orange-600">
                                <AlertCircle className="h-4 w-4" />
                                {t('pomodoro.review.aiAnalysis.weaknesses')}
                              </h4>
                              <ul className="space-y-1">
                                {(detailData.llmFocusEvaluation as any).analysis.weaknesses.map(
                                  (weakness: string, idx: number) => (
                                    <li key={idx} className="text-muted-foreground flex items-start gap-2 text-sm">
                                      <span className="mt-1 text-orange-600">!</span>
                                      <span>{weakness}</span>
                                    </li>
                                  )
                                )}
                              </ul>
                            </div>
                          )}

                          {/* Suggestions */}
                          <div>
                            <h4 className="mb-2 flex items-center gap-2 text-sm font-medium text-blue-600">
                              <Lightbulb className="h-4 w-4" />
                              {t('pomodoro.review.aiAnalysis.suggestions')}
                            </h4>
                            <ul className="space-y-1">
                              {(detailData.llmFocusEvaluation as any).analysis.suggestions.map(
                                (suggestion: string, idx: number) => (
                                  <li key={idx} className="text-muted-foreground flex items-start gap-2 text-sm">
                                    <span className="mt-1 text-blue-600">→</span>
                                    <span>{suggestion}</span>
                                  </li>
                                )
                              )}
                            </ul>
                          </div>

                          {/* Distraction warning */}
                          {(detailData.llmFocusEvaluation as any).distractionPercentage > 0 && (
                            <div className="rounded-lg border border-orange-200 bg-orange-50 p-4">
                              <div className="mb-2 flex items-center gap-2">
                                <AlertCircle className="h-4 w-4 text-orange-600" />
                                <h4 className="text-sm font-medium text-orange-900">
                                  {t('pomodoro.review.aiAnalysis.distractionAlert')}
                                </h4>
                              </div>
                              <p className="text-sm text-orange-700">
                                {t('pomodoro.review.aiAnalysis.distractionText', {
                                  percentage: (detailData.llmFocusEvaluation as any).distractionPercentage
                                })}
                              </p>
                            </div>
                          )}
                        </CollapsibleContent>
                      </Collapsible>
                    </CardContent>
                  </Card>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onOpenChange={(open) => {
          if (!isDeleting) {
            setDeleteDialogOpen(open)
          }
        }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('pomodoro.review.deleteConfirmTitle')}</DialogTitle>
            <DialogDescription>
              {t('pomodoro.review.deleteConfirmDescription', {
                count: (detailData?.focusMetrics as any)?.activityCount || 0
              })}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)} disabled={isDeleting}>
              {t('common.cancel')}
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={isDeleting}>
              {isDeleting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              {t('common.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
