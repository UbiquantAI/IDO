import { cn } from '@/lib/utils'

interface FlipDigitProps {
  digit: string
  phase: 'work' | 'break' | 'completed'
}

/**
 * Reusable flip-card digit component for Pomodoro countdown
 * Features phase-aware styling and maintains flip effect with top/bottom halves
 */
export function FlipDigit({ digit, phase }: FlipDigitProps) {
  return (
    <div className="relative h-28 w-20">
      <div
        className={cn(
          'relative h-full w-full overflow-hidden rounded-lg border-2 shadow-lg',
          'bg-gray-900 text-gray-100 dark:bg-gray-100 dark:text-gray-900',
          'transition-colors duration-300',
          phase === 'work' && 'border-primary/20',
          phase === 'break' && 'border-chart-2/20',
          phase === 'completed' && 'border-muted/20'
        )}>
        {/* Top half */}
        <div className="absolute inset-x-0 top-0 h-1/2 overflow-hidden rounded-t-lg">
          <div className="flex h-28 items-center justify-center font-mono text-6xl font-bold tabular-nums">{digit}</div>
        </div>

        {/* Bottom half */}
        <div className="absolute inset-x-0 bottom-0 h-1/2 overflow-hidden rounded-b-lg">
          <div className="flex h-28 -translate-y-14 items-center justify-center font-mono text-6xl font-bold tabular-nums">
            {digit}
          </div>
        </div>

        {/* Center divider line */}
        <div className="bg-border absolute top-1/2 right-0 left-0 h-px -translate-y-1/2" />
      </div>
    </div>
  )
}
