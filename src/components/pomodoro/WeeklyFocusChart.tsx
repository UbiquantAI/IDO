import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'

interface DailyFocusData {
  day: string
  sessions: number
  minutes: number
}

interface WeeklyFocusChartProps {
  data: DailyFocusData[]
}

export function WeeklyFocusChart({ data }: WeeklyFocusChartProps) {
  const { t } = useTranslation()

  // Find max minutes for scaling
  const maxMinutes = Math.max(...data.map((d) => d.minutes), 1)

  return (
    <Card className="shadow-none">
      <CardHeader>
        <CardTitle className="text-base">{t('pomodoro.review.weeklyFocus.title')}</CardTitle>
        <p className="text-muted-foreground text-sm">{t('pomodoro.review.weeklyFocus.subtitle')}</p>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {data.map((item) => {
            const percentage = (item.minutes / maxMinutes) * 100

            return (
              <div key={item.day} className="flex items-center gap-3">
                <div className="text-muted-foreground w-12 text-sm">{item.day}</div>
                <div className="flex-1">
                  <div className="bg-muted h-8 overflow-hidden rounded-full">
                    <div
                      className={cn(
                        'bg-primary flex h-full items-center justify-end pr-3 transition-all duration-500',
                        item.sessions === 0 && 'bg-muted'
                      )}
                      style={{ width: `${percentage}%` }}>
                      {item.sessions > 0 && (
                        <span className="text-primary-foreground text-xs font-medium">
                          {item.sessions} {t('pomodoro.review.weeklyFocus.sessions')} · {item.minutes}{' '}
                          {t('pomodoro.review.weeklyFocus.minutes')}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
