import { Clock, Activity } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'

interface SessionListItemProps {
  session: {
    id: string
    user_intent: string
    actual_duration_minutes?: number
    pure_work_duration_minutes?: number
    status: string
    start_time?: string
  }
  activityCount: number
  isSelected?: boolean
  onClick: () => void
}

export function SessionListItem({ session, activityCount, isSelected, onClick }: SessionListItemProps) {
  const { t } = useTranslation()

  // Format time from ISO string
  const formatTime = (isoString?: string) => {
    if (!isoString) return ''
    try {
      const date = new Date(isoString)
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } catch {
      return ''
    }
  }

  return (
    <div
      onClick={onClick}
      className={cn(
        'border-border hover:bg-muted/50 cursor-pointer rounded-lg border p-3 transition-colors',
        isSelected && 'bg-muted border-primary'
      )}>
      <div className="mb-2 flex items-start justify-between gap-2">
        <h4 className="line-clamp-2 flex-1 text-sm font-medium">{session.user_intent}</h4>
        {session.start_time && (
          <span className="text-muted-foreground shrink-0 text-xs">{formatTime(session.start_time)}</span>
        )}
      </div>
      <div className="text-muted-foreground flex items-center gap-3 text-xs">
        <div className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          <span>
            {session.pure_work_duration_minutes || 0} {t('pomodoro.review.focusMetrics.minutes')}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Activity className="h-3 w-3" />
          <span>
            {activityCount}{' '}
            {activityCount === 1
              ? t('pomodoro.review.activityTimeline.activity')
              : t('pomodoro.review.activityTimeline.activities')}
          </span>
        </div>
      </div>
    </div>
  )
}
