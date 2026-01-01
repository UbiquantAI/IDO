import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Card, CardContent } from '@/components/ui/card'

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

  // For now, we'll use placeholder values since the API might not exist yet
  // This can be connected to real data later
  useEffect(() => {
    // TODO: Connect to real API when available
    // For now, show zeros as placeholders
    setStats({
      completedToday: 0,
      focusMinutes: 0,
      focusHours: 0
    })
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
    <Card className="border-border">
      <CardContent className="py-4">
        <div className="divide-border grid grid-cols-3 divide-x">
          {statItems.map((item, index) => (
            <div key={index} className="flex flex-col items-center gap-1 px-4">
              <span className="text-3xl font-bold tabular-nums">{item.value}</span>
              <span className="text-muted-foreground text-xs">{item.label}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
