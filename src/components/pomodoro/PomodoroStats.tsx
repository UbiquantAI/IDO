import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Card, CardContent } from '@/components/ui/card'
import { getPomodoroStats } from '@/lib/client/apiClient'

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
      label: t('pomodoro.stats.completedToday')
    },
    {
      value: stats.focusMinutes,
      label: t('pomodoro.stats.focusMinutes')
    },
    {
      value: stats.focusHours,
      label: t('pomodoro.stats.focusHours')
    }
  ]

  return (
    <Card className="shadow-none">
      <CardContent className="py-4">
        <div className="divide-border grid grid-cols-3 divide-x">
          {statItems.map((item, index) => (
            <div key={index} className="flex flex-col items-center gap-1 px-4">
              <span className="text-3xl font-bold tabular-nums">{loading ? '-' : item.value}</span>
              <span className="text-muted-foreground text-xs">{item.label}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
