import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { CheckCircle2, Clock, Flame } from 'lucide-react'

import { getPomodoroStats } from '@/lib/client/apiClient'
import { cn } from '@/lib/utils'

interface StatsData {
  completedToday: number
  focusMinutes: number
  focusHours: number
}

/**
 * Statistics panel showing Pomodoro session metrics
 * - Completed today
 * - Focus minutes today
 * - Total focus hours
 */
export function PomodoroStats() {
  const { t } = useTranslation()
  const [stats, setStats] = useState<StatsData>({
    completedToday: 0,
    focusMinutes: 0,
    focusHours: 0
  })
  const [loading, setLoading] = useState(true)

  // Fetch today's statistics
  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true)
        const today = new Date().toISOString().split('T')[0] // YYYY-MM-DD format

        const result = await getPomodoroStats({ date: today })

        if (result.success && result.data) {
          const focusHours = Math.floor(result.data.totalFocusMinutes / 60)

          setStats({
            completedToday: result.data.completedCount,
            focusMinutes: result.data.totalFocusMinutes,
            focusHours: focusHours
          })
        }
      } catch (error) {
        console.error('[PomodoroStats] Failed to fetch statistics:', error)
        // Keep showing zeros on error
      } finally {
        setLoading(false)
      }
    }

    fetchStats()

    // Refresh stats every minute to catch new completed sessions
    const interval = setInterval(fetchStats, 60000)

    return () => clearInterval(interval)
  }, [])

  const statItems = [
    {
      value: stats.completedToday,
      label: t('pomodoro.stats.completedToday'),
      icon: CheckCircle2,
      color: 'text-chart-2'
    },
    {
      value: stats.focusMinutes,
      label: t('pomodoro.stats.focusMinutes'),
      icon: Clock,
      color: 'text-chart-3'
    },
    {
      value: stats.focusHours,
      label: t('pomodoro.stats.focusHours'),
      icon: Flame,
      color: 'text-chart-4'
    }
  ]

  return (
    <div className="flex items-center justify-between gap-2">
      {statItems.map((item, index) => {
        const Icon = item.icon
        return (
          <div key={index} className="group flex flex-1 items-center justify-center gap-2">
            <div
              className={cn(
                'rounded-lg p-2 ring-1 transition-all duration-300',
                'bg-muted/30 ring-border/40 group-hover:bg-muted/40'
              )}>
              <Icon className={cn('h-3.5 w-3.5 transition-all duration-300 group-hover:scale-110', item.color)} />
            </div>
            <div className="flex flex-col items-center gap-0.5">
              <span
                className={cn(
                  'text-[18px] font-bold tabular-nums transition-all duration-500',
                  loading ? 'opacity-50 blur-sm' : 'blur-0 opacity-100'
                )}>
                {loading ? '-' : item.value}
              </span>
              <span className="text-muted-foreground text-center text-[11px] leading-tight font-medium">
                {item.label}
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
