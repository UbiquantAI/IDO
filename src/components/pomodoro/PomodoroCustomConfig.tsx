import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { ChevronUp, ChevronDown, Clock, Coffee, Repeat, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { usePomodoroStore } from '@/lib/stores/pomodoro'
import { cn } from '@/lib/utils'

interface PomodoroCustomConfigProps {
  onClose?: () => void
}

/**
 * Custom configuration panel for Pomodoro settings
 * Allows adjusting work duration, break duration, and total rounds
 */
export function PomodoroCustomConfig({ onClose }: PomodoroCustomConfigProps) {
  const { t } = useTranslation()
  const { config, setConfig, setSelectedPresetId } = usePomodoroStore()

  const adjustValue = useCallback(
    (field: keyof typeof config, delta: number) => {
      const currentValue = config[field]
      let newValue = currentValue + delta

      // Set limits based on field
      if (field === 'totalRounds') {
        newValue = Math.max(1, Math.min(8, newValue))
      } else if (field === 'workDurationMinutes') {
        newValue = Math.max(5, Math.min(120, newValue))
      } else if (field === 'breakDurationMinutes') {
        newValue = Math.max(1, Math.min(60, newValue))
      }

      setConfig({ ...config, [field]: newValue })
      // Clear preset selection when custom values are used
      setSelectedPresetId(null)
    },
    [config, setConfig, setSelectedPresetId]
  )

  const configItems = [
    {
      field: 'workDurationMinutes' as const,
      icon: Clock,
      iconColor: 'text-primary',
      borderColor: 'border-primary/40',
      label: t('pomodoro.config.workDuration'),
      value: config.workDurationMinutes,
      unit: t('pomodoro.config.minutes'),
      increment: 5
    },
    {
      field: 'breakDurationMinutes' as const,
      icon: Coffee,
      iconColor: 'text-chart-2',
      borderColor: 'border-chart-2/40',
      label: t('pomodoro.config.breakDuration'),
      value: config.breakDurationMinutes,
      unit: t('pomodoro.config.minutes'),
      increment: 1
    },
    {
      field: 'totalRounds' as const,
      icon: Repeat,
      iconColor: 'text-muted-foreground',
      borderColor: 'border-muted-foreground/40',
      label: t('pomodoro.config.totalRounds'),
      value: config.totalRounds,
      unit: t('pomodoro.config.rounds'),
      increment: 1
    }
  ]

  return (
    <Card className="border-border bg-muted/20">
      <CardContent className="relative py-4">
        {onClose && (
          <Button variant="ghost" size="icon" className="absolute top-2 right-2 h-8 w-8" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        )}

        <div className="flex items-center justify-center gap-6">
          {configItems.map((item) => {
            const Icon = item.icon

            return (
              <div key={item.field} className="flex flex-col items-center gap-2">
                {/* Up Arrow */}
                <Button
                  variant="ghost"
                  size="icon"
                  className="hover:bg-muted/50 h-8 w-8"
                  onClick={() => adjustValue(item.field, item.increment)}>
                  <ChevronUp className="h-5 w-5" />
                </Button>

                {/* Value Circle */}
                <div
                  className={cn(
                    'flex h-20 w-20 flex-col items-center justify-center rounded-full border-2',
                    'bg-background shadow-sm',
                    item.borderColor
                  )}>
                  <span className="text-2xl font-bold tabular-nums">{item.value}</span>
                  <span className="text-muted-foreground text-xs">{item.unit}</span>
                </div>

                {/* Down Arrow */}
                <Button
                  variant="ghost"
                  size="icon"
                  className="hover:bg-muted/50 h-8 w-8"
                  onClick={() => adjustValue(item.field, -item.increment)}>
                  <ChevronDown className="h-5 w-5" />
                </Button>

                {/* Icon */}
                <Icon className={cn('h-4 w-4', item.iconColor)} />
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
