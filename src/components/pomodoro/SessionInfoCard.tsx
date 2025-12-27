import { useTranslation } from 'react-i18next'
import { CheckSquare, Clock, Coffee } from 'lucide-react'

import { Card, CardContent } from '@/components/ui/card'
import { usePomodoroStore } from '@/lib/stores/pomodoro'
import { cn } from '@/lib/utils'

/**
 * Session information card with phase-colored gradient background
 * Prominently displays current task and phase status
 */
export function SessionInfoCard() {
  const { t } = useTranslation()
  const { session } = usePomodoroStore()

  if (!session) {
    return null
  }

  const currentPhase = session.currentPhase || 'work'
  const isWorkPhase = currentPhase === 'work'
  const isBreakPhase = currentPhase === 'break'

  // Session title: prioritize associated TODO, fallback to user intent
  const sessionTitle = session.associatedTodoTitle || session.userIntent || t('pomodoro.intent.current')

  // Phase-specific styling
  const phaseConfig = {
    work: {
      gradient: 'from-primary/5 to-primary/10',
      border: 'border-primary/40',
      iconBg: 'bg-primary/10',
      iconColor: 'text-primary',
      badgeBg: 'bg-primary/10',
      icon: Clock,
      label: t('pomodoro.phase.work')
    },
    break: {
      gradient: 'from-chart-2/5 to-chart-2/10',
      border: 'border-chart-2/40',
      iconBg: 'bg-chart-2/10',
      iconColor: 'text-chart-2',
      badgeBg: 'bg-chart-2/10',
      icon: Coffee,
      label: t('pomodoro.phase.break')
    },
    completed: {
      gradient: 'from-muted/5 to-muted/10',
      border: 'border-muted/40',
      iconBg: 'bg-muted/10',
      iconColor: 'text-muted-foreground',
      badgeBg: 'bg-muted/10',
      icon: CheckSquare,
      label: t('pomodoro.phase.completed')
    }
  }

  const config = isWorkPhase ? phaseConfig.work : isBreakPhase ? phaseConfig.break : phaseConfig.completed
  const PhaseIcon = config.icon

  return (
    <Card
      className={cn(
        'border-2 shadow-lg transition-all duration-300',
        'bg-linear-to-br',
        config.gradient,
        config.border
      )}>
      <CardContent className="p-3">
        <div className="flex items-center justify-between gap-2.5">
          {/* Left: Icon + Task name */}
          <div className="flex min-w-0 flex-1 items-center gap-2">
            <div className={cn('shrink-0 rounded-full p-1.5', config.iconBg)}>
              <CheckSquare className={cn('h-4 w-4', config.iconColor)} />
            </div>

            <div className="min-w-0 flex-1">
              <div className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
                {t('pomodoro.intent.current')}
              </div>
              <div className="truncate text-lg font-semibold" title={sessionTitle}>
                {sessionTitle}
              </div>
            </div>
          </div>

          {/* Right: Phase badge */}
          <div className={cn('flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5', config.badgeBg)}>
            <PhaseIcon className={cn('h-4 w-4', config.iconColor)} />
            <span className={cn('text-sm font-semibold', config.iconColor)}>{config.label}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
